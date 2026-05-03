import os
import re
from pathlib import Path

from django.core.management.commands.startapp import Command as BaseCommand


class Command(BaseCommand):
    def handle(self, **options):
        super().handle(**options)

        app_name = options["name"]
        directory = options.get("directory")

        # Convert directory path to module notation, e.g. apps/home -> apps.home
        if directory:
            app_label = directory.strip("/").replace("/", ".").replace(os.sep, ".")
        else:
            app_label = app_name

        # Fix the generated apps.py so name matches the dotted module path
        app_dir = Path(directory) if directory else Path(app_name)
        apps_py = app_dir / "apps.py"
        if apps_py.exists():
            content = apps_py.read_text()
            content = re.sub(
                rf"""name\s*=\s*['"]{re.escape(app_name)}['"]""",
                f'name = "{app_label}"',
                content,
            )
            apps_py.write_text(content)

        # Ensure every parent package has an __init__.py
        for parent in app_dir.parents:
            if parent == Path("."):
                break
            init = parent / "__init__.py"
            if not init.exists():
                init.touch()

        settings_path = Path(
            os.environ["DJANGO_SETTINGS_MODULE"].replace(".", "/") + ".py"
        )
        text = settings_path.read_text()

        new_text = re.sub(
            r"(INSTALLED_APPS\s*=\s*\[.*?)(])",
            lambda m: m.group(1) + f'    "{app_label}",\n' + m.group(2),
            text,
            flags=re.DOTALL,
        )

        settings_path.write_text(new_text)
        self.stdout.write(self.style.SUCCESS(f"Added '{app_label}' to INSTALLED_APPS"))
