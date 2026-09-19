FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    xz-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Node.js from the official binary tarball rather than Debian's apt package -
# Debian's "npm" pulls in ~150 individually-packaged node-* dependencies
# (policy requires unbundling every JS dep), which is both slow and prone to
# mirror flakiness for something we only need to run eslint.
ENV NODE_VERSION=20.18.1
RUN curl -fsSL https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz

# ESLint for the JS/JSX portion of static analysis (Phase 4) - pinned to the
# v8 line since our bundled tooling/eslint.default.json uses the legacy
# .eslintrc-style flat config that v9 dropped by default.
RUN npm install -g eslint@8

COPY requirements.txt .
# Split so a flaky download of one of the large wheels (semgrep,
# tree_sitter_languages) doesn't force re-downloading everything else on
# retry - each RUN is its own cached layer. Deliberately NOT followed by a
# final `pip install -r requirements.txt` - pip's resolver re-fetches wheel
# metadata for full-file resolution even when a compatible version is
# already installed, which re-downloads the 70MB semgrep wheel for no
# reason. requirements.txt itself still lists every package (for anyone
# installing outside Docker); this is just how the image build applies it.
RUN pip install --no-cache-dir --timeout 30 --retries 15 \
    "fastapi>=0.100.0" "uvicorn>=0.22.0" "pydantic>=2.0.0" "sqlalchemy>=2.0.0" \
    "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4" "python-multipart>=0.0.6" \
    "pytest>=7.4.0" "httpx>=0.24.1" "bcrypt==4.0.1" "python-dotenv>=1.0.0" \
    "email-validator>=2.0.0" "psycopg2-binary>=2.9.9" "alembic>=1.13.0" \
    "celery>=5.3.6" "redis>=5.0.1" "datasketch>=1.6.4" "pylint>=3.0.0" "docker>=7.0.0"
# tree_sitter_languages 1.10.2 (latest release) was never updated for the
# tree-sitter 0.22+ Language() constructor signature change - installing
# plain tree-sitter would pull the newest version and get_parser() would
# raise "TypeError: __init__() takes exactly 1 argument (2 given)".
RUN pip install --no-cache-dir --timeout 30 --retries 15 "tree-sitter==0.21.3" "tree_sitter_languages>=1.10.2"
RUN pip install --no-cache-dir --timeout 30 --retries 15 "semgrep>=1.45.0"
RUN pip install --no-cache-dir --timeout 30 --retries 15 "faster-whisper>=1.0.0" "python-pptx>=0.6.23"
# google-generativeai (classic SDK) is deprecated/EOL and buggy with
# Pydantic ge/le constraints in response_schema - google-genai is current.
RUN pip install --no-cache-dir --timeout 30 --retries 15 "google-genai>=1.0.0" "tenacity>=8.2.0"

# Bake the Whisper model into the image at build time instead of leaving it
# to download on first real use - avoids a runtime network dependency (and
# an unpredictable first-request delay) inside the worker/api containers.
ARG WHISPER_MODEL_SIZE=base
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL_SIZE}', device='cpu', compute_type='int8')"

# requirements.txt is NOT re-read by pip after this point (see note above) -
# this import/binary smoke test is what actually catches "added a package to
# requirements.txt but forgot to add it to one of the RUN lines above" at
# build time instead of as a runtime ModuleNotFoundError (this has happened
# twice already: tree_sitter_languages/datasketch, then docker).
RUN python -c "\
import fastapi, uvicorn, pydantic, sqlalchemy, jose, passlib, multipart, pytest, httpx, bcrypt; \
import dotenv, email_validator, psycopg2, alembic, celery, redis, pylint; \
import tree_sitter_languages, datasketch, docker; \
import faster_whisper, pptx; \
from google import genai; import tenacity; \
print('all critical imports OK')" \
    && semgrep --version && eslint --version && ffmpeg -version | head -1

COPY . .

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
