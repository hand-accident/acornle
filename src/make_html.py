import codecs
import pathlib
import subprocess
import sys
from itertools import zip_longest
import json

import cytoolz as tz
import yattag


def to_file_and_open(path: pathlib.Path, force_overwrite=True):
    def _wrapper(func):
        def _inner(*args, **kwargs):
            if force_overwrite:
                path.unlink(missing_ok=True)
            sys.stdout = codecs.open(
                str(path.resolve()), 'ab', 'utf-8', 'ignore')
            func(*args, **kwargs)
            sys.stdout = sys.__stdout__
            subprocess.Popen(path.name, shell=True, cwd=path.parent).wait()

        return _inner

    return _wrapper


class HTMLGenerator:
    def __init__(self, title='', style=''):
        self.doc, self.tag, self.text, self.line = yattag.Doc().ttl()
        self.title = title
        self.style = style

    def generate(self):
        self.doc.asis('<!DOCTYPE html>')  # noqa
        with self.tag('html', lang='ja'):
            with self.tag('head'):
                self.header()
            with self.tag('body'):
                self.body()

    def header(self):
        self.doc.stag('meta', charset='utf-8')
        self.line('title', self.title)
        self.line('style', self.style)

    def body(self):
        raise NotImplementedError

    def out(self):
        print(yattag.indent(self.doc.getvalue()))

    def ex_line(self, tag_name, content):
        if callable(content):
            with self.tag(tag_name):
                content()
        else:
            self.line(tag_name, content)

    def table(self, contents, header=False, index=None, row_ids=None, **kwargs):
        if index is None:
            index = []
        if row_ids is None:
            row_ids = []

        if row_ids and len(row_ids) == len(contents):
            z = [(c, {'id': i}) for c, i in zip(contents, row_ids)]
        else:
            z = [(c, dict()) for c in contents]

        with self.tag('table', **kwargs):
            if header and index:
                with self.tag('thead'):  # noqa
                    with self.tag('tr'):
                        for i in index:
                            self.ex_line('th', i)

            with self.tag('tbody'):  # noqa
                for row, id_kw in z:
                    with self.tag('tr', **id_kw):
                        for c in row:
                            self.ex_line('td', c)

    def jump_to_id(self, id_, display_name):
        with self.tag('a', href=f'#{id_}'):
            self.text(display_name)

    def jump_to_file(self, path: pathlib.Path, display_name):
        with self.tag('a', href=f'file:///{path.resolve()}',
                      target='_blank', rel='noopener noreferrer'):  # noqa
            self.text(display_name)

    def u_list(self, content):
        with self.tag('ul'):
            for c in content:
                self.ex_line('li', c)


def subtitle(text, size=2):
    def wrapper(func):
        def _subtitle(self: HTMLGenerator, *args, **kwargs):
            self.line(f'h{size}', text)
            func(self, *args, **kwargs)
            self.doc.stag('hr')

        return _subtitle

    return wrapper

class AcornHTML(HTMLGenerator):
    def __init__(self):
        self.data = {}
        super().__init__(title='acornle', style='h2, h3, a, td {font-family: monospace;}')
        self.generate()

    def body(self):
        with open(pathlib.Path(__file__).parent / 'acorn.json', mode='r') as f:
            self.data = json.load(f)

        self.recursive_gen('', '', self.data)

    def gen_div(self, parent_id, r, d):
        key = get_key(d)

        if parent_id:
            id_ = f'{parent_id}-{r}'
        else:
            id_ = key

        @subtitle(id_)
        def division(self):
            def _inner(responce, _body):
                if isinstance(_body, dict):
                    next_key = get_key(_body)
                    return lambda: self.jump_to_id(f'{id_}-{responce}', f'{responce}: {next_key}')
                elif isinstance(_body, str):
                    return f'{responce}: {_body}🌰'
                else:
                    raise TypeError

            if parent_id:
                self.line('h3', key)

            if (bodies:= len(d[key])) > 81:
                count = 27
            elif bodies > 54:
                count = 18
            else:
                count = 9

            self.table(zip_longest(
                *tz.partition_all(
                    count, 
                    [_inner(responce, _body) for responce, _body in d[key].items()]),
                fillvalue=''))

            with self.tag('div'):
                self.doc.stag('br')
                self.jump_to_id(parent_id, '↑')
                self.jump_to_id('slate', '🌰')

        with self.tag('div', id=id_):
            division(self)

    def recursive_gen(self, parent_id, responce, d):
        self.gen_div(parent_id, responce, d)

        if parent_id:
            id_ = f'{parent_id}-{responce}'
        else:
            id_ = get_key(d)

        [self.recursive_gen(f'{id_}', _r, _body) 
         for _r, _body in 
         d[get_key(d)].items() if isinstance(_body, dict)]


def get_key(_body):
    return list(_body)[0]


def main():
    a = AcornHTML()
    to_file_and_open(pathlib.Path('__file__').parent / 'index_link.html')(a.out)()

if __name__ == '__main__':
    main()
