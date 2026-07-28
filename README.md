# Radar de Editais FUNPEC

Ferramenta para buscar automaticamente editais de subvenção econômica, chamadas
públicas e editais de fomento publicados no Diário Oficial da União — sem
precisar saber programar ou usar o Google Colab.

Tem duas partes, que usam o mesmo motor de busca por trás:

1. **Plataforma web** (`app.py`) — qualquer pessoa da FUNPEC abre um link no
   navegador, escolhe os parâmetros (ou usa os padrões) e clica em **Buscar**.
   Vê os resultados na tela, baixa em Excel ou manda por e-mail na hora.
2. **Robô diário** (`email_digest.py` + GitHub Actions) — roda sozinho todo
   dia útil de manhã e manda um e-mail com o resumo, sem ninguém precisar
   abrir nada.

Custo: **R$ 0,00**. Tudo roda em serviços gratuitos (GitHub + Streamlit
Community Cloud), sem precisar de servidor próprio.

---

## Passo a passo para colocar no ar (feito uma única vez)

Isso aqui é a única parte "técnica", e só precisa ser feita uma vez por
alguém com uma conta no GitHub (pode ser você mesmo, não precisa saber
programar de verdade, é só seguir os passos).

### 1. Criar o repositório no GitHub

1. Crie uma conta gratuita em [github.com](https://github.com) (se ainda não tiver).
2. Clique em **New repository**, dê um nome (ex: `radar-editais-funpec`) e
   marque como **Private** se não quiser que fique público.
3. Envie todos os arquivos desta pasta para esse repositório (pelo site do
   GitHub mesmo: **Add file → Upload files**, arraste tudo e clique em
   **Commit changes**).

### 2. Publicar a plataforma web (Streamlit Community Cloud)

1. Acesse [share.streamlit.io](https://share.streamlit.io) e entre com a
   conta do GitHub.
2. Clique em **New app**, escolha o repositório que você criou, e em
   **Main file path** selecione `app.py`.
3. Clique em **Deploy**. Em 1–2 minutos a plataforma estará no ar com um
   link fixo (algo como `https://radar-editais-funpec.streamlit.app`).
4. Compartilhe esse link com quem for usar na FUNPEC — é só clicar e abrir
   no navegador, celular ou computador, sem instalar nada.

> Se quiser trocar o botão "Enviar por e-mail" dentro da plataforma web,
> configure as credenciais de e-mail também nesse app: no painel do
> Streamlit Cloud, vá em **Settings → Secrets** e adicione:
> ```
> EMAIL_REMETENTE = "radar.editais.funpec@gmail.com"
> EMAIL_SENHA_APP = "xxxxxxxxxxxxxxxx"
> ```
> (veja o passo 4 abaixo para gerar a senha de app do Gmail)

### 3. Colocar o logo da FUNPEC (opcional)

Coloque o arquivo de logo (PNG) dentro da pasta com o nome `logo_funpec.png`
e, no arquivo `app.py`, remova o `#` da linha:
```python
# st.sidebar.image("logo_funpec.png", use_container_width=True)
```

### 4. Configurar o e-mail automático

O robô diário usa uma conta do Gmail para enviar os e-mails. Recomenda-se
criar uma conta só para isso (ex: `radar.editais.funpec@gmail.com`), mas
também funciona com uma conta institucional já existente.

1. Na conta do Gmail que vai enviar os e-mails, ative a **verificação em
   duas etapas** (em myaccount.google.com/security).
2. Ainda em Segurança, procure **Senhas de app** (App Passwords), crie uma
   nova senha para "Radar Editais FUNPEC" — o Google vai gerar um código de
   16 letras. Guarde esse código.
3. No repositório do GitHub, vá em **Settings → Secrets and variables →
   Actions → New repository secret** e crie três segredos:
   - `EMAIL_REMETENTE` → o e-mail do Gmail (ex: `radar.editais.funpec@gmail.com`)
   - `EMAIL_SENHA_APP` → o código de 16 letras gerado no passo anterior
   - `DIGEST_DESTINATARIOS` → os e-mails que vão receber o resumo diário,
     separados por vírgula (ex: `fulano@funpec.br, ciclana@funpec.br`)

Pronto — o arquivo `.github/workflows/daily_digest.yml` já está configurado
para rodar automaticamente **todo dia útil às 8h (horário de Brasília)** e
mandar o e-mail. Para testar sem esperar o horário, vá na aba **Actions** do
repositório, escolha o workflow "Radar de Editais FUNPEC" e clique em
**Run workflow**.

---

## Uso do dia a dia (para quem não mexeu na configuração)

- **Quer pesquisar algo específico agora?** Abra o link da plataforma web,
  ajuste o período/instituições se quiser, clique em **Buscar Editais**.
- **Quer só acompanhar o que aparece?** Não precisa fazer nada — o e-mail
  automático chega todo dia útil de manhã.

## Ajustando instituições e termos monitorados por padrão

Edite a lista em `dou_radar.py` (`INSTITUICOES_PADRAO` e `TERMOS_PADRAO`) —
essa mudança vale tanto para a plataforma web quanto para o e-mail
automático, porque os dois usam o mesmo arquivo.

## Limitações a ter em mente

- A busca depende da disponibilidade do site in.gov.br; instabilidades lá
  podem fazer alguns dias/termos retornarem vazios mesmo havendo publicação.
- Buscas muito amplas (muitas instituições × muitos termos × muitos dias)
  podem levar alguns minutos — a barra de progresso na plataforma web mostra
  o andamento.
- O Streamlit Community Cloud gratuito "dorme" o app depois de um tempo sem
  uso; a primeira pessoa a abrir no dia pode esperar ~30s para ele acordar.
