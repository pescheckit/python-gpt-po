#!/bin/bash
set -e

# Display help information if no arguments are provided
if [ $# -eq 0 ]; then
  VERSION=$(python -m python_gpt_po.main --version)
  echo "GPT PO Translator Docker Container v$VERSION"
  echo "==========================================="
  echo 
  echo "Usage: docker run [docker options] ghcr.io/pescheckit/python-gpt-po [translator options]"
  echo
  echo "Volume Mounting:"
  echo "  You can mount any directory from your host system to any path inside the container."
  echo "  Format: -v /host/path:/container/path"
  echo "  The '/container/path' is what you'll use with the --folder parameter."
  echo
  echo "Examples:"
  echo "  # Translate files in the current directory to German"
  echo "  docker run -v $(pwd):/data -e OPENAI_API_KEY=<your_key> ghcr.io/pescheckit/python-gpt-po --folder /data --lang de"
  echo
  echo "  # Use an absolute path to a different directory"
  echo "  docker run -v /home/user/translations:/translations -e OPENAI_API_KEY=<your_key> ghcr.io/pescheckit/python-gpt-po --folder /translations --lang fr,es"
  echo
  echo "  # Windows example (PowerShell)"
  echo "  docker run -v C:/Users/username/projects/locales:/locales -e OPENAI_API_KEY=<your_key> ghcr.io/pescheckit/python-gpt-po --folder /locales --lang de"
  echo
  echo "  # MacOS example"
  echo "  docker run -v /Users/username/Documents/translations:/input -e OPENAI_API_KEY=<your_key> ghcr.io/pescheckit/python-gpt-po --folder /input --lang fr,es"
  echo
  echo "  # List available models (no need for --folder or --lang)"
  echo "  docker run -e OPENAI_API_KEY=<your_key> ghcr.io/pescheckit/python-gpt-po --provider openai --list-models"
  echo
  echo "For full documentation, visit: https://github.com/pescheckit/python-gpt-po"
  exit 0
fi

# Check if we need to display version
if [ "$1" = "--version" ]; then
  python -m python_gpt_po.main --version
  exit 0
fi

# Check if we need to display help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  python -m python_gpt_po.main --help
  exit 0
fi

# Execute command with args
exec python -m python_gpt_po.main "$@"
