# Radar de Editais e Licitações FUNPEC

Ferramenta para buscar automaticamente:
1. **Editais de fomento** — subvenção econômica, chamadas públicas e editais
   de fomento publicados no Diário Oficial da União (DOU).
2. **Licitações** — compras e contratações publicadas no Portal Nacional de
   Contratações Públicas (PNCP), para quando a FUNPEC/NTCPP quer prestar
   serviços técnicos a outros órgãos.

Sem precisar saber programar ou usar o Google Colab.

Tem duas partes, que usam o mesmo motor de busca por trás:

1. **Plataforma web** (`app.py`) — qualquer pessoa da FUNPEC abre um link no
   navegador, escolhe os parâmetros na aba desejada (Editais ou Licitações,
   ou usa os padrões) e clica em **Buscar**. Vê os resultados na tela, baixa
   em Excel ou manda por e-mail na hora.
2. **Robô diário** (`email_digest.py` + GitHub Actions) — roda sozinho todo
   dia útil de manhã e manda um e-mail com o resumo das duas fontes juntas,
   sem ninguém precisar abrir nada.

Custo: **R$ 0,00**. Tudo roda em serviços gratuitos (GitHub + Streamlit
Community Cloud), sem precisar de servidor próprio.

> ⚠️ **Sobre a aba de Licitações (PNCP):** diferente da busca no DOU (que já
> foi testada em uso real), a integração com o PNCP foi construída a partir
> da documentação oficial da API e de exemplos públicos, mas **ainda não foi
> validada contra a API real**. Rode um teste manual assim que publicar — se
> algum campo vier vazio ou com nome diferente do esperado, é só me mostrar
> o resultado (ou o erro) que eu ajusto o código em `pncp_radar.py`.

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
mandar o e-mail com os resultados do DOU e do PNCP juntos. Para testar sem
esperar o horário, vá na aba **Actions** do repositório, escolha o workflow
"Radar de Editais FUNPEC" e clique em **Run workflow**.

Se quiser que o e-mail diário traga só os editais de fomento (sem
licitações) enquanto a integração com o PNCP está sendo validada, crie mais
um secret: `DIGEST_INCLUIR_PNCP` com o valor `false`.

---

## Uso do dia a dia (para quem não mexeu na configuração)

- **Quer pesquisar algo específico agora?** Abra o link da plataforma web,
  ajuste o período/instituições se quiser, clique em **Buscar Editais**.
- **Quer só acompanhar o que aparece?** Não precisa fazer nada — o e-mail
  automático chega todo dia útil de manhã.

### Como adicionar uma palavra-chave própria (sem editar código)

Nos campos "Órgãos e instituições a monitorar" e "Termos que caracterizam um
edital" (e o equivalente na aba de Licitações), é possível digitar algo que
não está na lista pronta:

1. Clique dentro da caixa.
2. Digite a palavra ou expressão que você quer adicionar (ex: `hidrogênio verde`).
3. Aperte **Enter** — ela aparece como uma nova "pílula" selecionada, junto
   com as que já estavam lá.

Isso vale só para aquela busca (não fica salvo depois que a página for
recarregada). Se quiser que um termo apareça sempre, por padrão, para todo
mundo, é a mudança permanente descrita na seção seguinte.

## Ajustando instituições, modalidades e termos monitorados por padrão

- **Editais de fomento (DOU):** edite `INSTITUICOES_PADRAO` e `TERMOS_PADRAO`
  em `dou_radar.py`.
- **Licitações (PNCP):** edite `MODALIDADES_PADRAO` e `TERMOS_PADRAO` em
  `pncp_radar.py`. Os termos são comparados com o texto do objeto da
  contratação (ex: "cimentação de poços", "ensaios laboratoriais").

Essas mudanças valem tanto para a plataforma web quanto para o e-mail
automático, porque os dois usam os mesmos arquivos.

## Testando a aba de Licitações (PNCP) pela primeira vez

1. Abra a plataforma web e vá na aba **📄 Licitações (PNCP)**.
2. Reduza "Dias corridos para trás" para 1 ou 2, para o teste ser rápido.
3. Clique em **Buscar Licitações**.
4. Se aparecer um erro ou os resultados vierem sempre vazios mesmo com
   critérios amplos, me mande o print — é bem provável que seja só um ajuste
   pequeno de nome de campo no `pncp_radar.py`, já que essa integração ainda
   não tinha sido validada contra a API real quando foi construída.

## Limitações a ter em mente

- A busca depende da disponibilidade do site in.gov.br; instabilidades lá
  podem fazer alguns dias/termos retornarem vazios mesmo havendo publicação.
- Buscas muito amplas (muitas instituições × muitos termos × muitos dias)
  podem levar alguns minutos — a barra de progresso na plataforma web mostra
  o andamento.
- O Streamlit Community Cloud gratuito "dorme" o app depois de um tempo sem
  uso; a primeira pessoa a abrir no dia pode esperar ~30s para ele acordar.
