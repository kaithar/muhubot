from time import strftime

def basic_rss(body):
    message = '[{0}] New: {1} ({2} - Updated: {3})'.format(body['tag'], body['item']['title'], body['item']['link'], strftime('%a, %d %b %Y %H:%M:%S %z', tuple(body['item']['updated_parsed'])))
    return message

def crunchyroll(body):
    area = []
    if 'gb' in body['item']['media_restriction']['content']: area.append('gb')
    if 'us' in body['item']['media_restriction']['content']: area.append('us')

    area = ', '.join(area)
    message = '[crunchyroll] Release: {crunchyroll_seriestitle} Ep {crunchyroll_episodenumber} - {crunchyroll_episodetitle} (id: {crunchyroll_mediaid}, region flags: '.format(**body['item'])+area+', has '+str(len(body['item']['media_restriction']['content']))+' regions)'
    #, body['item']['crunchyroll_premiumpubdate'], item.crunchyroll_freepubdate
    return message
