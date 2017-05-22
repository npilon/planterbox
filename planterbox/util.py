def clean_dict_repr(mw):
    """Produce a repr()-like output of dict mw with ordered keys"""
    return '{' + \
           ', '.join('{k!r}: {v!r}'.format(k=k, v=v) for k, v in
                     sorted(mw.items())) +\
           '}'
