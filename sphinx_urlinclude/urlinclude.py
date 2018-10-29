from hashlib import shake_128 as sha
import os
from docutils.parsers.rst import directives
from sphinx.directives.code import LiteralInclude
from sphinx.ext.intersphinx import _read_from_url
from sphinx.util.docutils import SphinxDirective
from sphinx.ext.autodoc import Options, get_documenters
from docutils import nodes, utils

from sphinx.util.nodes import split_explicit_title


class Urlinclude(SphinxDirective):
    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'branch': directives.unchanged,
        'github': directives.unchanged,
    }

    def run(self):
        conf_dict = self.env.app.config.urlinclude_config
        if self.options:
            conf_dict[self.env.docname] = self.options.copy()

        return []


def make_giturl_role(app, config):
    def giturl(typ, rawtext, text, lineno, inliner, options={}, content=[]):

        text = utils.unescape(text)
        has_explicit_title, title, part = split_explicit_title(text)

        if app.env.docname in config:
            override = options
            options = config[app.env.docname].copy()
            options.update(override)

        github = options['github']
        branch = options.get('branch', 'master')

        uri = f"https://github.com/{github}/blob/{branch}/{part}"

        if not has_explicit_title:
            title = part

        pnode = nodes.reference(title, title, internal=False, refuri=uri)
        return [pnode], []

    return giturl


class UrlLiteralInclude(LiteralInclude):
    LiteralInclude.option_spec.update({
        'url': directives.uri,
        'branch': directives.unchanged,
        'github': directives.unchanged
    })

    def run(self):
        if 'url' in self.options or 'github' in self.options:
            conf_dict = self.env.app.config.urlinclude_config

            if self.env.docname in conf_dict:
                override = self.options
                self.options = conf_dict[self.env.docname].copy()
                self.options.update(override)

            build_dir = os.path.dirname(self.env.doctreedir)
            download_dir = os.path.join(build_dir, '_urlinclude')
            os.makedirs(download_dir, exist_ok=True)

            basename = self.arguments[0]

            if 'github' in self.options:
                branch_path = f"raw/{self.options.get('branch', 'master')}"
                repo_url = f"https://github.com/{self.options['github']}"
                url = f"{repo_url}/{branch_path}/{basename}"
            elif 'url' in self.options:
                url = f"{self.options['url']}"

            local_path = os.path.join(
                download_dir, f'{sha(url.encode("utf-8")).hexdigest(5)}.py')

            doc_path = os.path.dirname(self.env.doc2path(self.env.docname))

            local_rel_path = os.path.relpath(local_path, doc_path)

            if not os.path.isfile(local_path):
                print(f'Downloading: {url}')
                contents = _read_from_url(url, self.env.app.config).read()
                with open(local_path, 'w') as f:
                    f.write(contents.decode())

            self.arguments[0] = local_rel_path

        return super().run()


def setup(app):
    directives.register_directive('literalinclude', UrlLiteralInclude)
    app.add_config_value('urlinclude_config', {}, 'env')
    app.add_role('giturl',
                 make_giturl_role(app, app.config.urlinclude_config))
    directives.register_directive('urlinclude', Urlinclude)
