import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class MediaKlikkIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.)?
        (?:mediaklikk|m4sport|hirado)\.hu/.*?(?:videok?|cikk)/
        (?:(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/(?P<day>[0-9]{1,2})/)?
        (?:[^/#?]+/)?
        (?P<id>[^/#?_]+)'''

    _TESTS = [{
        # mediaklikk - category after date
        'url': 'https://mediaklikk.hu/video/2026/03/21/kultura/agenda-2026-marcius-21/',
        'info_dict': {
            'id': r're:^\d+$',
            'title': 'Agenda, 2026. március 21.',
            'display_id': 'agenda-2026-marcius-21',
            'ext': 'mp4',
            'upload_date': '20260321',
            'thumbnail': r're:^https?://(?:cdn\.cms\.mtv\.hu|mediaklikk\.cms\.mtv\.hu)/.+\.(?:jpe?g|png|webp)(?:\?.*)?$',
        },
    }, {
        # mediaklikk - date in html
        'url': 'https://mediaklikk.hu/video/a-dal-2026-harmadik-elodonto/',
        'info_dict': {
            'id': r're:^\d+$',
            'title': r're:^A Dal 2026,? Harmadik elődöntő$',
            'display_id': 'a-dal-2026-harmadik-elodonto',
            'ext': 'mp4',
            'upload_date': '20260321',
            'thumbnail': r're:^https?://(?:cdn\.cms\.mtv\.hu|mediaklikk\.cms\.mtv\.hu)/.+\.(?:jpe?g|png|webp)(?:\?.*)?$',
        },
    }, {
        # m4sport
        'url': 'https://m4sport.hu/video/2026/03/21/simon-ehammer-szurrealis-ez-az-eredmeny-minden-tokeletesen-ment-2',
        'info_dict': {
            'id': r're:^\d+$',
            'title': 'Simon Ehammer: Szürreális ez az eredmény, minden tökéletesen ment',
            'display_id': 'simon-ehammer-szurrealis-ez-az-eredmeny-minden-tokeletesen-ment-2',
            'ext': 'mp4',
            'upload_date': '20260321',
            'thumbnail': r're:^https?://(?:cdn\.cms\.mtv\.hu|mediaklikk\.cms\.mtv\.hu)/.+\.(?:jpe?g|png|webp)(?:\?.*)?$',
        },
    }, {
        # hirado
        'url': 'https://hirado.hu/video/2026/03/21/hirmusor/idojaras-jelentes-2026-marcius-21-12-30/',
        'info_dict': {
            'id': r're:^\d+$',
            'title': 'Időjárás-jelentés, 2026. március 21. 12:30',
            'display_id': 'idojaras-jelentes-2026-marcius-21-12-30',
            'ext': 'mp4',
            'upload_date': '20260321',
            'thumbnail': r're:^https?://(?:cdn\.cms\.mtv\.hu|mediaklikk\.cms\.mtv\.hu)/.+\.(?:jpe?g|png|webp)(?:\?.*)?$',
        },
    }, {
        # hirado - subcategory
        'url': 'https://hirado.hu/belfold/video/2026/03/22/valasztasok-a-magyar-tortenelemben-ezzel-a-cimmel-rendezett-konferenciat-a-rubicon-intezet-es-a-nemzeti-kozszolgalati-egyetem-2',
        'info_dict': {
            'id': r're:^\d+$',
            'title': 'Választások a magyar történelemben – ezzel a címmel rendezett konferenciát a Rubicon Intézet és a Nemzeti Közszolgálati Egyetem',
            'display_id': 'valasztasok-a-magyar-tortenelemben-ezzel-a-cimmel-rendezett-konferenciat-a-rubicon-intezet-es-a-nemzeti-kozszolgalati-egyetem-2',
            'ext': 'mp4',
            'upload_date': '20260322',
            'thumbnail': r're:^https?://(?:cdn\.cms\.mtv\.hu|mediaklikk\.cms\.mtv\.hu)/.+\.(?:jpe?g|png|webp)(?:\?.*)?$',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')

        webpage = self._download_webpage(url, display_id)

        player_data = self._search_json(
            r'loadPlayer\((?:\s*["\'][^"\']+["\']\s*,)?',
            webpage, 'player data', mobj)

        video_id = str(player_data['contentId'])
        title = player_data.get('title') or self._og_search_title(webpage, fatal=False) or \
            self._html_search_regex(r'<h\d+\b[^>]+\bclass="article_title">([^<]+)<', webpage, 'title')

        upload_date = unified_strdate(
            '{}-{}-{}'.format(mobj.group('year'), mobj.group('month'), mobj.group('day')))
        if not upload_date:
            upload_date = unified_strdate(self._html_search_regex(
                r'<p+\b[^>]+\bclass="article_date">([^<]+)<', webpage, 'upload date', default=None))

        player_data['video'] = urllib.parse.unquote(player_data.pop('token'))

        player_page = self._download_webpage(
            'https://player.mediaklikk.hu/playernew/player.php',
            video_id, query=player_data, headers={'Referer': url})

        player_json = self._search_json(
            r'\bpl\.setup\s*\(', player_page, 'player json', video_id, end_pattern=r'\);')

        playlist_urls = traverse_obj(
            player_json, ('playlist', lambda _, v: v.get('type') == 'hls', 'file', {url_or_none})) or []

        if not playlist_urls:
            raise ExtractorError('Unable to extract playlist url')

        formats, subtitles = [], {}
        for idx, playlist_url in enumerate(dict.fromkeys(playlist_urls)):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                playlist_url, video_id, m3u8_id=f'hls-{idx}', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if not formats:
            raise ExtractorError('Unable to extract formats')

        self._remove_duplicate_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'upload_date': upload_date,
            'thumbnail': player_data.get('bgImage') or self._og_search_thumbnail(webpage),
        }
