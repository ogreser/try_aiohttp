import re
import aiohttp
import asyncio


TAG_RE = re.compile(r'<[^>]+>')
NOT_WORDS_RE = re.compile(r'[^\w]')
SPACES_RE = re.compile(r'\s{2,}')


def normalize_text(text):
    result = TAG_RE.sub(' ', text.lower())
    result = NOT_WORDS_RE.sub(' ', result)
    result = SPACES_RE.sub(' ', result)
    return result.strip()


class MentionCounter:
    def __init__(self, text):
        self._title = text
        self._regex = re.compile(r'\b{}\b'.format(normalize_text(text)))
        self._count = 0

    @property
    def title(self):
        return self._title

    @property
    def count(self):
        return self._count

    def process_text(self, text):
        self._count += len(self._regex.findall(text))


class MentionsCounteUpdater:
    LAST_DOC_ID_URL = 'https://hacker-news.firebaseio.com/v0/maxitem.json'
    DOC_URL_TEMPLATE = 'https://hacker-news.firebaseio.com/v0/item/{doc_id}.json'
    UPDATE_PERIOD = 30.0
    WATCH_TYPES = ['story'] 

    def __init__(self, update_period=None, watch_types=None, start_from_doc=None):
        self._counters = []
        self._last_processed_doc_id = start_from_doc
        self._update_period = update_period or self.UPDATE_PERIOD
        self._watch_types = watch_types or self.WATCH_TYPES
        self._processed_items_count = 0

    def add_counter(self, counter):
        self._counters.append(counter)

    def get_current_state(self):
        return {
            'processed_items': self._processed_items_count,
            'counters': {
                c.title: c.count
                for c in self._counters
            }
        }

    def _process_text(self, text):
        normalized_text = normalize_text(text)
        for counter in self._counters:
            counter.process_text(normalized_text)
        self._processed_items_count += 1

    async def _get_doc_by_id(self, session, doc_id):
        url = self.DOC_URL_TEMPLATE.format(doc_id=doc_id)
        resp = await session.get(url)
        return await resp.json()

    async def _get_last_doc_id(self, session):
        resp = await session.get(self.LAST_DOC_ID_URL)
        doc_id = int(await resp.json())
        return doc_id

    async def updates_iter_loop(self, session):
        while True:
            if self._last_processed_doc_id is None:
                self._last_processed_doc_id = await self._get_last_doc_id(session)
                await asyncio.sleep(self._update_period)
            last_doc_id = await self._get_last_doc_id(session)
            while last_doc_id > self._last_processed_doc_id:
                next_doc_id = self._last_processed_doc_id + 1
                doc = await self._get_doc_by_id(session, next_doc_id)
                if doc['type'] in self._watch_types and not doc.get('deleted'):
                    self._process_text(doc['title'])
                    yield self.get_current_state()
                self._last_processed_doc_id = next_doc_id
