# Política de Privacidade — EsportesMundo

**Última atualização:** 2026-04-26

## 1. Coleta de dados

O EsportesMundo **não coleta dados pessoais de terceiros**. O sistema opera exclusivamente com dados públicos de esportes (placar, times, notícias) obtidos via APIs abertas.

## 2. Uso das APIs de plataformas

O sistema utiliza as APIs oficiais do TikTok, Instagram (Meta), YouTube e Facebook exclusivamente para publicar conteúdo esportivo automaticamente. Nenhum dado de usuários dessas plataformas é lido, armazenado ou processado.

## 3. Tokens de acesso

Os tokens de acesso às APIs (META_ACCESS_TOKEN, YOUTUBE_API_KEY, TIKTOK_ACCESS_TOKEN, etc.) são armazenados **localmente** no arquivo `.env` do servidor onde o sistema roda. Esses tokens não são transmitidos a terceiros nem registrados em logs externos.

## 4. Banco de dados local

O banco SQLite (`esportes.db`) armazena apenas dados de conteúdo gerado (textos, caminhos de imagem, status de publicação). Nenhuma informação pessoal é gravada.

## 5. Contato

Dúvidas sobre privacidade: agenciaorigem360gestao@gmail.com
