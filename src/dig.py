from asyncio import to_thread
from datetime import datetime
from dns.exception import Timeout
import dns.flags
from dns.message import make_query
import dns.opcode
from dns.query import udp
import dns.rcode
import dns.rdataclass
import dns.rdatatype
from time import perf_counter

from src.utils import package_message

VALID_RECORD_TYPES = {"A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "SRV", "CAA", "PTR"}
DEFAULT_RECORD_TYPE = "A"
DEFAULT_NAMESERVER = "1.1.1.1"
NAME_WIDTH = 30
DATA_WIDTH = 7

async def dig(ctx, user_query):
    args = user_query.split()
    arg = args.pop(0)

    if arg[0] == '@':
        default_nameserver_used = False
        nameserver = arg[1:]
        
        if not args:
            await ctx.send("You must include a domain name to lookup. Use `$help dig` for more information.")
            return

        domain = args.pop(0)
    else:
        default_nameserver_used = True
        nameserver = DEFAULT_NAMESERVER
        domain = arg

    if args:
        record_type = args.pop(0).upper()
    else:
        record_type = DEFAULT_RECORD_TYPE

    if record_type not in VALID_RECORD_TYPES:
        await ctx.send(f"Unsupported record type `{record_type}`.\nSupported types include: `{', '.join(VALID_RECORD_TYPES)}`.")
        return

    await ctx.defer()

    server = nameserver
    port = 53
    protocol = "udp"

    try:
        rdtype = dns.rdatatype.from_text(record_type)
        query = make_query(qname=domain, rdtype=rdtype, use_edns=0, payload=512)
        start = perf_counter()
        response = await to_thread(udp, query, server, timeout=5, port=port)
        
        if response.rcode() == dns.rcode.NXDOMAIN:
            await ctx.send(f"`{domain}` does not exist.")
            return

        elapsed_ms = round((perf_counter() - start) * 1000)
        output = build_dig_output(
                user_query=user_query,
                default_nameserver_used=default_nameserver_used,
                query=query,
                response=response,
                server=server,
                port=port,
                elapsed_ms=elapsed_ms,
                protocol=protocol
        )
    except Timeout:
        await ctx.send(f"DNS lookup timeout out for `{domain}`.")
        return
    except ValueError as e:
        await ctx.send(f"`{server}` is not a valid DNS server address. Use an IPv4 or IPv6 address like `1.1.1.1` or `8.8.8.8`.")
        return
    except Exception as e:
        await ctx.send(f"DNS lookup failed: `{type(e).__name__}: {e}`")
        return
    
    await package_message(f"```text\n{output}\n```", ctx)

def build_dig_output(*, user_query, default_nameserver_used, query, response, server, port, elapsed_ms, protocol):
    opcode = dns.opcode.to_text(response.opcode())
    status = dns.rcode.to_text(response.rcode())
    flags = format_flags(response.flags)
    query_count = len(response.question)
    answer_count = section_rr_count(response.answer)
    authority_count = section_rr_count(response.authority)
    additional_count = section_rr_count(response.additional) + 1 if response.opt else 0
    when = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
    msg_size = len(response.to_wire())

    parts = [f"; <<>> DiG-ish Karn Edition <<>> {user_query}"]

    if not default_nameserver_used:
        parts.append("; (1 server found)")

    parts.extend(
        [
            ";; global options: +cmd",
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

    if opt_section := format_opt_pseudosection(response):
        parts.append(opt_section)

    parts.append(format_question_section(response))
    parts.append('')

    if answer_section := format_rrset_section("ANSWER", response.answer):
        parts.append(answer_section)
        parts.append('')

    if authority_section := format_rrset_section("AUTHORITY", response.authority):
        parts.append(authority_section)
        parts.append('')

    if additional_section := format_rrset_section("ADDITIONAL", [i for i in response.additional if i.rdtype != dns.rdatatype.OPT]):
        parts.append(additional_section)
        parts.append('')

    parts.extend(
        [
            f";; Query time: {elapsed_ms} msec",
            f";; SERVER: {server}#{port}({server}) ({protocol.upper()})",
            f";; WHEN: {when}",
            f";; MSG SIZE rcvd: {msg_size}"
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

def format_question_section(response):
    lines = [";; QUESTION SECTION:"]

    for question in response.question:
        name = question.name.to_text()
        rdclass = dns.rdataclass.to_text(question.rdclass)
        rdtype = dns.rdatatype.to_text(question.rdtype)
        lines.append(f";{name:<{NAME_WIDTH + DATA_WIDTH}} {rdclass:<{DATA_WIDTH}} {rdtype}")

    return '\n'.join(lines)

def format_rrset_section(title, section):
    if not section:
        return ''

    lines = [f";; {title} SECTION:"]

    for rrset in section:
        name = rrset.name.to_text()
        rdclass = dns.rdataclass.to_text(rrset.rdclass)
        rdtype = dns.rdatatype.to_text(rrset.rdtype)

        lines.extend(f"{name:<{NAME_WIDTH}} {rrset.ttl:<{DATA_WIDTH}} {rdclass:<{DATA_WIDTH}} {rdtype:<{DATA_WIDTH}} {i.to_text()}" for i in rrset)

    return '\n'.join(lines)
