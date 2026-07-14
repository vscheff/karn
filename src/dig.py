from asyncio import to_thread
from datetime import datetime
from dns.exception import Timeout
import dns.flags
from dns.message import make_query
import dns.name
import dns.opcode
from dns.query import tcp, udp
import dns.rcode
import dns.rdataclass
import dns.rdatatype
from ipaddress import ip_address
from random import choice
from time import perf_counter

from src.utils import get_flags, package_message

HEADER_LINE = "; <<>> DiG-ish Karn Edition <<>> "
VALID_RECORD_TYPES = {"A", "AAAA", "ANY", "CAA", "CNAME", "DNSKEY", "DS", "MX", "NAPTR", "NS", "PTR", "SOA", "SRV", "TXT", "TLSA", "URI"}
DEFAULT_RECORD_TYPE = "A"
REVERSE_RECORD_TYPE = "PTR"
DEFAULT_NAMESERVER = "1.1.1.1"
DEFAULT_PORT = 53
NAME_WIDTH = 30
DATA_WIDTH = 7
TRACE_MAX_STEPS = 20

ROOT_SERVERS = [
    # IPv4
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
    "199.7.91.13",      # d.root-servers.net
    "192.203.230.10",   # e.root-servers.net
    "192.5.5.241",      # f.root-servers.net
    "192.112.36.4",     # g.root-servers.net
    "198.97.190.53",    # h.root-servers.net
    "192.36.148.17",    # i.root-servers.net
    "192.58.128.30",    # j.root-servers.net
    "193.0.14.129",     # k.root-servers.net
    "199.7.83.42",      # l.root-servers.net
    "202.12.27.33",     # m.root-servers.net
]

async def dig(ctx, user_query):
    flags, args = get_flags(user_query, make_dic=True, no_args=['x'], plus_args=True)
    arg = args.pop(0)

    if not (default_nameserver_used := not arg[0] == '@'):
        if not args:
            await ctx.send("You must include a domain name to lookup. Use `$help dig` for more information.")
            return

        nameserver = arg[1:]
        domain = args.pop(0)
    else:
        nameserver = DEFAULT_NAMESERVER
        domain = arg

    if reverse_lookup := 'x' in flags:
        try:
            domain = get_reverse_lookup_name(domain)
        except ValueError as e:
            await ctx.send(str(e))
            return

    record_type = args.pop(0).upper() if args else REVERSE_RECORD_TYPE if reverse_lookup else DEFAULT_RECORD_TYPE

    if record_type not in VALID_RECORD_TYPES:
        await ctx.send(f"Unsupported record type `{record_type}`.\nSupported types include: `{', '.join(VALID_RECORD_TYPES)}`.")
        return

    if (options := await build_options(ctx, flags)) is None:
        return

    await ctx.defer()

    try:
        rdtype = dns.rdatatype.from_text(record_type)
        
        if "trace" in flags:
            output = await trace_lookup(domain, nameserver, rdtype, record_type, user_query, options, default_nameserver_used)
        else:
            query = make_query(qname=domain, rdtype=rdtype, use_edns=0, payload=512, want_dnssec=options["use_dnssec"])
            start = perf_counter()
            response = await send_dns_query(query, nameserver, options)
            
            if response.rcode() == dns.rcode.NXDOMAIN:
                await ctx.send(f"`{domain}` does not exist.")
                return

            elapsed_ms = round((perf_counter() - start) * 1000)
            
            if "short" in flags:
                output = format_short_answer(response)
            else:
                output = build_dig_output(
                        user_query=user_query,
                        default_nameserver_used=default_nameserver_used,
                        query=query,
                        response=response,
                        server=nameserver,
                        elapsed_ms=elapsed_ms,
                        options=options
                )
    except Timeout:
        await ctx.send(f"DNS lookup timeout out for `{domain}`.")
    except ValueError as e:
        await ctx.send(f"`{nameserver}` is not a valid DNS server address. Use an IPv4 or IPv6 address like `1.1.1.1` or `8.8.8.8`.")
    except Exception as e:
        await ctx.send(f"DNS lookup failed: `{type(e).__name__}: {e}`")
    else:
        if not output:
            return

        await package_message(f"```text\n{output}\n```", ctx)

async def build_options(ctx, flags):
    no_all = "noall" in flags

    options = {
            "port": DEFAULT_PORT,
            "show_cmd": not no_all,
            "show_comments": not no_all,
            "show_question": not no_all,
            "show_answer": not no_all,
            "show_authority": not no_all,
            "show_additional": not no_all,
            "show_stats": not no_all,
            "use_dnssec": False,
            "use_tcp": False
    }

    if "cmd" in flags:
        options["show_cmd"] = True
    if "nocmd" in flags:
        options["show_cmd"] = False
    if "comments" in flags:
        options["show_comments"] = True
    if "nocomments" in flags:
        options["show_comments"] = False
    if "question" in flags:
        options["show_question"] = True
    if "noquestion" in flags:
        options["show_question"] = False
    if "answer" in flags:
        options["show_answer"] = True
    if "noanswer" in flags:
        options["show_answer"] = False
    if "authority" in flags:
        options["show_authority"] = True
    if "noauthority" in flags:
        options["show_authority"] = False
    if "additional" in flags:
        options["show_additional"] = True
    if "noadditional" in flags:
        options["show_additional"] = False
    if "stats" in flags:
        options["show_stats"] = True
    if "nostats" in flags:
        options["show_stats"] = False
    if "tcp" in flags:
        options["use_tcp"] = True
    if any(i in flags for i in ["trace", "dnssec", "do"]):
        options["use_dnssec"] = True
    if "nodnssec" in flags or "nodo" in flags:
        options["use_dnssec"] = False
    if "p" in flags:
        try:
            options["port"] = int(flags["p"])

            if not 0 < options["port"] < 65535:
                raise ValueError
        except ValueError:
            await ctx.send("Bad argument given for Port. Please use a valid integer in the range [0, 65535].")
            
            return None

    return options

async def trace_lookup(domain, nameserver, rdtype, record_type, user_query, options, default_nameserver_used):
    qname = dns.name.from_text(domain)
    current_servers = ROOT_SERVERS[:]
    output_parts = []
    
    if cmd_header := get_cmd_header(user_query, options, default_nameserver_used):
        output_parts.append(cmd_header)

    try:
        root_response, elapsed_ms = await get_root_priming_response(nameserver, options)
        output_parts.append(format_trace_response(root_response, nameserver, elapsed_ms, options, include_additional=False))
    except Exception:
        pass

    for step in range(TRACE_MAX_STEPS):
        server = choice(current_servers)

        response, elapsed_ms = await trace_query(qname, rdtype, server, options)

        output_parts.append(format_trace_response(response, server, elapsed_ms, options))

        if response.answer or response.rcode() != dns.rcode.NOERROR:
            return "\n\n".join(output_parts)

        if not (ns_names := get_authority_ns_names(response)):
            output_parts.append("; Trace stopped: no answer and no NS delegation found.")
            
            return "\n\n".join(output_parts)

        if not (next_servers := get_glue_addresses(response)):
            if not (next_servers := await resolve_nameserver_addresses(ns_names, nameserver, options)):
                    output_parts.append("; Trace stopped: could not resolve next nameserver addresses.")
                    
                    return "\n\n".join(output_parts)

        current_servers = next_servers

    output_parts.append(f"; Trace stopped after {TRACE_MAX_STEPS} steps.")
    
    return "\n\n".join(output_parts)

async def get_root_priming_response(nameserver, options):
    query = make_query(qname='.', rdtype=dns.rdatatype.NS, use_edns=0, payload=1232, want_dnssec=options["use_dnssec"])

    start = perf_counter()
    response = await send_dns_query(query, nameserver, options)
    elapsed_ms = round((perf_counter() - start) * 1000)

    return response, elapsed_ms

async def trace_query(qname, rdtype, server, options):
    query = make_query(qname=qname, rdtype=rdtype, use_edns=0, payload=1232, want_dnssec=options["use_dnssec"])
    query.flags &= ~dns.flags.RD
    
    start = perf_counter()
    response = await send_dns_query(query, server, options)
    elapsed_ms = round((perf_counter() - start) * 1000)

    return response, elapsed_ms

async def send_dns_query(query, server, options, *, timeout=5):
    query_func = tcp if options["use_tcp"] else udp

    return await to_thread(query_func, query, server, timeout=timeout, port=options["port"])

def format_rrset_lines(rrset):
    name = rrset.name.to_text()
    rdclass = dns.rdataclass.to_text(rrset.rdclass)
    rdtype = dns.rdatatype.to_text(rrset.rdtype)

    return [f"{name:<{NAME_WIDTH}} {rrset.ttl:<{DATA_WIDTH}} {rdclass:<{DATA_WIDTH}} {rdtype:<{DATA_WIDTH}} {i.to_text()}" for i in rrset]

def get_authority_ns_names(response):
    ns_names = []

    for rrset in response.authority:
        if rrset.rdtype == dns.rdatatype.NS:
            ns_names.extend(i.target.to_text() for i in rrset)
    
    return ns_names

def get_glue_addresses(response):
    addresses = []

    for rrset in response.additional:
        if rrset.rdtype == dns.rdatatype.A:
            addresses.extend(i.address for i in rrset)

    return addresses

async def resolve_nameserver_addresses(ns_names, nameserver, options):
    addresses = []
    rdtype = dns.rdatatype.from_text("A")

    for ns_name in ns_names:
        try:
            query = make_query(qname=ns_name, rdtype=rdtype, use_edns=0, payload=1232, want_dnssec=options["use_dnssec"])
            response = await send_dns_query(query, nameserver, options)

            for rrset in response.answer:
                if rrset.rdtype == dns.rdatatype.A:
                    addresses.extend(i.address for i in rrset)
        except Exception:
            continue

    return addresses

def format_trace_response(response, server, elapsed_ms, options, include_additional=False):
    lines = []

    for rrset in response.answer:
        lines.extend(format_rrset_lines(rrset))

    for rrset in response.authority:
        lines.extend(format_rrset_lines(rrset))

    if include_additional:
        for rrset in response.additional:
            if rrset.rdtype != dns.rdatatype.OPT:
                lines.extend(format_rrset_lines(rrset))

    if not lines:
        status = dns.rcode.to_text(response.rcode())
        lines.append(f";; status: {status}")

    lines.append(f";; Received {len(response.to_wire())} bytes from {server}#{options['port']}({server}) in {elapsed_ms} ms")

    return "\n".join(lines)

def format_rrset_lines(rrset):
    name = rrset.name.to_text()
    rdclass = dns.rdataclass.to_text(rrset.rdclass)
    rdtype = dns.rdatatype.to_text(rrset.rdtype)

    return [f"{name:<{NAME_WIDTH}} {rrset.ttl:<{DATA_WIDTH}} {rdclass:<{DATA_WIDTH}} {rdtype:<{DATA_WIDTH}} {i.to_text()}" for i in rrset]

def get_reverse_lookup_name(address):
    try:
        ip = ip_address(address)
    except ValueError:
        raise ValueError(f"`{address}` is not a valid IPv4 or IPv6 address for reverse lookup.")

    return ip.reverse_pointer

def format_short_answer(response):
    lines = []

    for rrset in response.answer:
        for item in rrset:
            lines.append(item.to_text())

    return '\n'.join(lines) or "No Answer"

def get_cmd_header(user_query, options, default_nameserver_used):
    parts = []

    if options["show_cmd"]:
        parts.append(f"{HEADER_LINE}{user_query}")

        if not default_nameserver_used:
            parts.append("; (1 server found)")

        parts.append(";; global options: +cmd")

    return '\n'.join(parts)

def build_dig_output(*, user_query, default_nameserver_used, query, response, server, elapsed_ms, options):
    opcode = dns.opcode.to_text(response.opcode())
    status = dns.rcode.to_text(response.rcode())
    flags = format_flags(response.flags)
    query_count = len(response.question)
    answer_count = section_rr_count(response.answer)
    authority_count = section_rr_count(response.authority)
    additional_count = section_rr_count(response.additional) + (1 if response.opt else 0)
    when = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
    msg_size = len(response.to_wire())

    parts = []

    if cmd_header := get_cmd_header(user_query, options, default_nameserver_used):
        parts.append(cmd_header)

    if options["show_comments"]:
        parts.extend(
            [
                ";; Got answer:",
                f";; ->>HEADER<<- opcode: {opcode}, status: {status}, id: {response.id}",
                (
                    f";; flags: {flags}; "
                    f"QUERY: {query_count}, "
                    f"ANSWER: {answer_count}, "
                    f"AUTHORITY: {authority_count}, "
                    f"ADDITIONAL: {additional_count}"
                ),
                "",
            ]
        )

    if (opt_section := format_opt_pseudosection(response)) and options["show_comments"]:
        parts.append(opt_section)

    if options["show_question"]:
        parts.append(format_question_section(response, options["show_comments"]))
        
        if options["show_comments"]:
            parts.append('')

    if options["show_answer"] and \
       (answer_section := format_rrset_section("ANSWER", response.answer, options["show_comments"])):
        
        parts.append(answer_section)
        
        if options["show_comments"]:
            parts.append('')

    if options["show_authority"] and \
       (authority_section := format_rrset_section("AUTHORITY", response.authority, options["show_comments"])):
        
        parts.append(authority_section)
        
        if options["show_comments"]:
            parts.append('')

    filtered_additional = [i for i in response.additional if i.rdtype != dns.rdatatype.OPT]

    if options["show_additional"] and \
       (additional_section := format_rrset_section("ADDITIONAL", filtered_additional, options["show_comments"])):
        
        parts.append(additional_section)
        
        if options["show_comments"]:
            parts.append('')

    if options["show_stats"]:
        transport = "TCP" if options["use_tcp"] else "UDP"

        parts.extend(
            [
                f";; Query time: {elapsed_ms} msec",
                f";; SERVER: {server}#{options['port']}({server}) ({transport})",
                f";; WHEN: {when}",
                f";; MSG SIZE  rcvd: {msg_size}"
            ]
        )

    return '\n'.join(parts)

def format_flags(flags):
    text = dns.flags.to_text(flags)

    return text.lower() if text else ''

def section_rr_count(section):
    return sum(len(i) for i in section)

def format_opt_pseudosection(response):
    if not response.opt:
        return ''

    if not (flags_text := dns.flags.edns_to_text(response.ednsflags)):
        flags_text = ''

    return f";; OPT PSEUDOSECTION:\n; EDNS: version: {response.edns}, flags:{flags_text}; udp: {response.payload}"

def format_question_section(response, show_comments):
    lines = [";; QUESTION SECTION:"] if show_comments else []

    for question in response.question:
        name = question.name.to_text()
        rdclass = dns.rdataclass.to_text(question.rdclass)
        rdtype = dns.rdatatype.to_text(question.rdtype)
        lines.append(f";{name:<{NAME_WIDTH + DATA_WIDTH}} {rdclass:<{DATA_WIDTH}} {rdtype}")

    return '\n'.join(lines)

def format_rrset_section(title, section, show_comments):
    if not section:
        return ''

    lines = [f";; {title} SECTION:"] if show_comments else []

    for rrset in section:
        name = rrset.name.to_text()
        rdclass = dns.rdataclass.to_text(rrset.rdclass)
        rdtype = dns.rdatatype.to_text(rrset.rdtype)

        lines.extend(f"{name:<{NAME_WIDTH}} {rrset.ttl:<{DATA_WIDTH}} {rdclass:<{DATA_WIDTH}} {rdtype:<{DATA_WIDTH}} {i.to_text()}" for i in rrset)

    return '\n'.join(lines)
