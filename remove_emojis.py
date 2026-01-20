#!/usr/bin/env python3
"""
Remove all emojis from Python and Markdown files.

This script scans all .py and .md files and removes emoji characters,
replacing them with text equivalents where appropriate.
"""

import os
import re
from pathlib import Path


# Emoji mappings to text
EMOJI_REPLACEMENTS = {
    '[OK]': '[OK]',
    '[ERROR]': '[ERROR]',
    '[WARNING]': '[WARNING]',
    '[WARNING]': '[WARNING]',
    '[REFRESH]': '[REFRESH]',
    '[CHANNEL]': '[CHANNEL]',
    '[TIME]': '[TIME]',
    '[KEY]': '[KEY]',
    '[STOP]': '[STOP]',
    '[WAIT]': '[WAIT]',
    '[OK]': '[OK]',
    '[FAIL]': '[FAIL]',
    '[VIDEO]': '[VIDEO]',
    '[CAMERA]': '[CAMERA]',
    '[TARGET]': '[TARGET]',
    '[DESIGN]': '[DESIGN]',
    '[MUSIC]': '[MUSIC]',
    '[VOICE]': '[VOICE]',
    '[CHART]': '[CHART]',
    '[TRENDING]': '[TRENDING]',
    '[DOWN]': '[DOWN]',
    '[NOTE]': '[NOTE]',
    '[FOLDER]': '[FOLDER]',
    '[FOLDER]': '[FOLDER]',
    '[SAVE]': '[SAVE]',
    '[CONFIG]': '[CONFIG]',
    '[BUILD]': '[BUILD]',
    '[SETTINGS]': '[SETTINGS]',
    '[SETTINGS]': '[SETTINGS]',
    '[LAUNCH]': '[LAUNCH]',
    '[IDEA]': '[IDEA]',
    '[SUCCESS]': '[SUCCESS]',
    '[BUG]': '[BUG]',
    '[LOCKED]': '[LOCKED]',
    '[UNLOCKED]': '[UNLOCKED]',
    '[STAR]': '[STAR]',
    '[STAR]': '[STAR]',
    '[WINNER]': '[WINNER]',
    '[GOOD]': '[GOOD]',
    '[BAD]': '[BAD]',
    '[100]': '[100]',
    '[HOT]': '[HOT]',
    '[COLD]': '[COLD]',
    '[COLD]': '[COLD]',
}


def remove_emojis_from_text(text):
    """Remove emojis from text, replacing with text equivalents."""
    result = text

    # Replace known emojis
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        result = result.replace(emoji, replacement)

    # Remove any remaining emojis (Unicode emoji ranges)
    # This regex covers most emoji characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+",
        flags=re.UNICODE
    )

    result = emoji_pattern.sub('', result)

    return result


def process_file(file_path):
    """Process a single file to remove emojis."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        new_content = remove_emojis_from_text(content)

        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to remove emojis from all Python and Markdown files."""
    print("Removing emojis from all Python and Markdown files...")
    print("=" * 70)

    # Get all .py and .md files
    python_files = list(Path('.').rglob('*.py'))
    markdown_files = list(Path('.').rglob('*.md'))

    all_files = python_files + markdown_files

    # Exclude certain directories
    excluded_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv', 'node_modules'}
    all_files = [
        f for f in all_files
        if not any(excluded in f.parts for excluded in excluded_dirs)
    ]

    print(f"Found {len(all_files)} files to process")
    print()

    modified_count = 0
    for file_path in all_files:
        if process_file(file_path):
            print(f"Modified: {file_path}")
            modified_count += 1

    print()
    print("=" * 70)
    print(f"Completed! Modified {modified_count} files")


if __name__ == '__main__':
    main()
