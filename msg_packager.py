def package_message(obj):
    if isinstance(obj, (int, float)):
        obj = str(obj)
    elif isinstance(obj, (list, set, tuple)):
        obj = ', '.join([str(i) for i in obj])
    elif isinstance(obj, dict):
        obj = ', '.join([str(i) for i in obj.items()])
    ret_list = []
    while len(obj) >= 2000:
        ret_list.append(obj[:2000])
        obj = obj[2000:]
    ret_list.append(obj)
    return ret_list
