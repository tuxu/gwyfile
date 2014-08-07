def find_datafields(obj):
    """ Return pairs of (``number``, ``title``) for all available
        data fields in ``obj``.
    """
    token = '/data/title'
    channels = [int(k[1:-len(token)]) for k, v in obj.iteritems()
                if k.endswith(token)]
    titles = [obj['/{}/data/title'.format(ch)] for ch in channels]
    return zip(channels, titles)


def get_datafields(obj):
    """ Return a dictionary of titles and their corresponding data fields.
    """
    return {
        v: obj['/{chnum}/data'.format(chnum=k)]
        for k, v in find_datafields(obj)
    }
