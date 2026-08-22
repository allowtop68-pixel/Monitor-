#!/usr/bin/env python3
"""
monitor_instagram.py
Verifica a data e o link do último post de uma lista de perfis PÚBLICOS
do Instagram, e gera/atualiza um monitor.html com o resultado.

Requisitos:
    pip install instaloader

Uso:
    python monitor_instagram.py

Configuração:
    Edite o arquivo perfis.txt (um @usuario por linha, sem o @).

Aviso:
    - Não usa login: lê apenas dados públicos, de forma anônima.
    - Isso foge dos Termos de Uso do Instagram. Não é ilegal, mas o
      Instagram pode bloquear temporariamente o IP em caso de abuso.
    - O Instagram restringe cada vez mais o acesso anônimo; alguns perfis
      podem falhar mesmo sendo públicos. Isso é uma limitação da plataforma,
      não um bug do script.
    - Para uso comercial/confiável, prefira a Graph API oficial (exige
      conta Business/Creator e só funciona para contas que você administra).
"""

import json
import random
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import instaloader
except ImportError:
    sys.exit("Falta instalar a dependência: pip install instaloader")

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(exist_ok=True)

PERFIS_FILE = BASE_DIR / "perfis.txt"
DADOS_FILE = BASE_DIR / "dados.json"
HTML_FILE = DOCS_DIR / "index.html"

# Intervalo aleatório entre perfis, em segundos (evita padrão robótico)
ESPERA_MIN = 90
ESPERA_MAX = 180


def carregar_perfis():
    if not PERFIS_FILE.exists():
        PERFIS_FILE.write_text("# um @usuario por linha, sem o @\n# exemplo:\n# colinascomorleans\n")
        sys.exit(f"Criei {PERFIS_FILE.name} vazio. Preencha com os perfis e rode de novo.")
    linhas = PERFIS_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip().lstrip("@") for l in linhas if l.strip() and not l.strip().startswith("#")]


def carregar_dados_antigos():
    if DADOS_FILE.exists():
        try:
            return json.loads(DADOS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def verificar_perfil(loader, username):
    """Retorna dict com data (ISO) e link do último post, ou None em caso de falha."""
    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        if profile.is_private:
            print(f"  [aviso] @{username} é privado — pulando.")
            return None
        posts = profile.get_posts()
        primeiro_post = next(posts, None)
        if primeiro_post is None:
            print(f"  [aviso] @{username} não tem posts públicos visíveis.")
            return None
        data_iso = primeiro_post.date_utc.replace(tzinfo=timezone.utc).isoformat()
        link = f"https://www.instagram.com/p/{primeiro_post.shortcode}/"
        return {"data": data_iso, "link": link}
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"  [erro] @{username} não existe.")
        return None
    except instaloader.exceptions.ConnectionException as e:
        print(f"  [rate limit] Instagram sinalizou limite de requisições: {e}")
        raise  # propaga para parar o script inteiro, como descrito nas boas práticas
    except Exception as e:
        print(f"  [erro] @{username}: {e}")
        return None


def gerar_html(dados):
    linhas_json = json.dumps(dados, ensure_ascii=False, indent=2)
    atualizado_em = datetime.now().strftime("%d/%m/%Y às %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Diário de Publicações</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  :root{{--ink:#161a22;--paper:#eee9dc;--paper-dim:#e2dcca;--rule:#c9c1a8;--stamp:#a63d2f;--ok:#5a6b4f;}}
  *{{box-sizing:border-box;}}
  body{{background:var(--ink);color:var(--paper);font-family:'Source Serif 4',Georgia,serif;min-height:100vh;padding:32px 16px 80px;margin:0;}}
  .sheet{{max-width:760px;margin:0 auto 24px;background:var(--paper);color:var(--ink);border-radius:2px;box-shadow:0 30px 80px rgba(0,0,0,.45);padding:40px 36px 32px;}}
  .eyebrow{{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--stamp);font-weight:600;}}
  h1{{font-size:32px;margin:6px 0 4px;font-weight:600;}}
  h2{{font-size:17px;margin:0 0 14px;font-weight:600;}}
  .entries{{display:flex;flex-direction:column;}}
  .entry{{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:16px;padding:14px 4px;border-bottom:1px dashed var(--rule);}}
  .entry:last-child{{border-bottom:none;}}
  .stamp{{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.05em;padding:5px 9px;border-radius:999px;white-space:nowrap;border:1.5px solid currentColor;text-align:center;}}
  .stamp.fresh{{color:var(--ok);}}
  .stamp.stale{{color:var(--stamp);}}
  .meta .name{{font-size:16.5px;font-weight:600;}}
  .meta .date{{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#6b6552;margin-top:2px;}}
  .link a{{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--stamp);}}
  .link a:hover{{color:var(--stamp);}}
  .footnote{{margin-top:22px;font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#8a8570;text-align:center;}}
  .empty{{text-align:center;padding:36px 10px;color:#7a745f;font-family:'IBM Plex Mono',monospace;font-size:12.5px;}}
  @media (max-width:640px){{.sheet{{padding:26px 18px 22px;}} .entry{{grid-template-columns:1fr;row-gap:8px;}} .stamp{{justify-self:start;}}}}
</style>
</head>
<body>
  <div class="sheet">
    <div class="eyebrow">Diário de publicações</div>
    <h1>Monitor de Instagram</h1>
    <h2 style="font-weight:400;font-size:14px;color:#6b6552;">Atualizado automaticamente em {atualizado_em}</h2>
    <div class="entries" id="entries"></div>
    <div class="footnote">gerado por monitor_instagram.py</div>
  </div>
<script>
const dados = {linhas_json};
const entriesEl = document.getElementById('entries');
const usuarios = Object.keys(dados);

if(usuarios.length === 0){{
  entriesEl.innerHTML = '<div class="empty">Nenhum dado coletado ainda.</div>';
}} else {{
  const ordenados = usuarios
    .filter(u => dados[u] && dados[u].data)
    .sort((a,b) => new Date(dados[b].data) - new Date(dados[a].data));

  entriesEl.innerHTML = ordenados.map(u => {{
    const info = dados[u];
    const data = new Date(info.data);
    const hoje = new Date();
    const dias = Math.floor((hoje - data) / (1000*60*60*24));
    const fresh = dias <= 14;
    const label = dias === 0 ? 'hoje' : dias === 1 ? 'há 1 dia' : `há ${{dias}} dias`;
    const dataFmt = data.toLocaleDateString('pt-BR');
    return `
      <div class="entry">
        <div class="stamp ${{fresh ? 'fresh' : 'stale'}}">${{label}}</div>
        <div class="meta">
          <div class="name">@${{u}}</div>
          <div class="date">postou em ${{dataFmt}}</div>
        </div>
        <div class="link"><a href="${{info.link}}" target="_blank" rel="noopener">ver post →</a></div>
      </div>`;
  }}).join('');
}}
</script>
</body>
</html>
"""
    HTML_FILE.write_text(html, encoding="utf-8")


def main():
    perfis = carregar_perfis()
    if not perfis:
        sys.exit("Nenhum perfil em perfis.txt.")

    dados = carregar_dados_antigos()
    loader = instaloader.Instaloader(
        download_pictures=False, download_videos=False,
        download_video_thumbnails=False, download_geotags=False,
        download_comments=False, save_metadata=False, compress_json=False,
    )

    print(f"Verificando {len(perfis)} perfil(is)...")
    for i, username in enumerate(perfis, 1):
        print(f"[{i}/{len(perfis)}] @{username}")
        try:
            resultado = verificar_perfil(loader, username)
        except instaloader.exceptions.ConnectionException:
            print("Parando o script: Instagram sinalizou limite de requisições.")
            break
        if resultado:
            dados[username] = resultado

        if i < len(perfis):
            espera = random.randint(ESPERA_MIN, ESPERA_MAX)
            print(f"  aguardando {espera}s...")
            time.sleep(espera)

    DADOS_FILE.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    gerar_html(dados)
    print(f"\nPronto. {HTML_FILE.name} atualizado com {len(dados)} perfil(is).")


if __name__ == "__main__":
    main()
