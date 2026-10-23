# Guia do backoffice Diomika

O backoffice é a aplicação onde gere o catálogo da loja, os orçamentos, as encomendas e as
mensagens de contacto. Funciona em Windows, Mac e Linux e liga-se sozinho a `api.diomika.com`.

## Instalar e entrar

1. Instale com o ficheiro que recebeu (`Diomika-Backoffice-<versão>-setup.exe` no Windows,
   `.dmg` no Mac, `.AppImage` no Linux). Se o Windows avisar «Editor desconhecido», escolha
   **Mais informações → Executar mesmo assim** (a aplicação não tem certificado pago).
2. Entre com o seu utilizador e palavra-passe. Se a verificação em dois passos estiver activa,
   leia o código QR com uma app de autenticação (Google Authenticator, Microsoft Authenticator)
   e escreva o código de 6 dígitos.
3. Depois de 5 tentativas falhadas a conta fica bloqueada 15 minutos.

**Actualizações:** no Windows e no Linux a aplicação actualiza-se sozinha ao fechar. No Mac
aparece um aviso com a ligação para descarregar a versão nova.

## Catálogo

O catálogo organiza-se em **família de produto** (ex.: Almofadas) → **categoria**
(ex.: Almofadas de Natal) → **modelo** → **cores** e **produtos (EAN)**.

### Criar uma categoria
Em **Categorias → + Nova**, escolha a família e o nome. A família define os campos que os
modelos vão ter (tipo, dimensões, composição…).

### Criar um modelo e pô-lo na loja
1. Na categoria, **+ Adicionar** um modelo e **Guardar rascunho**. Fica oculto na loja.
2. Em **Cores do modelo**, **+ Adicionar cor** com número, nome e imagem.
3. Em **Produtos (EAN)**, **+ Adicionar produto** com o EAN-13 e a medida/altura.
4. Carregue em **Publicar na loja**. A aplicação recusa se faltar pelo menos uma cor com
   imagem ou um produto com EAN — a mensagem diz o que falta.

Regras:
- O **EAN é único em todo o catálogo**: não pode repetir-se entre famílias.
- **Ocultar** tira o modelo da loja sem o apagar.
- A loja mostra as alterações em segundos (a cache é renovada a cada gravação).

### Exportar e importar
Em cada lista, **Exportar CSV** descarrega os registos. A importação de CSV mostra primeiro
uma pré-visualização e só grava depois de confirmar.

## Orçamentos do site
Os pedidos feitos na loja aparecem em **Orçamentos do site**. Abra um para ver as linhas e
descarregar o PDF. Mude o estado à medida que avança com o cliente.

## Encomendas
Em **Encomendas → Nova encomenda interna** cria uma encomenda escolhendo modelo, medida/altura,
cor e quantidade (respeita a quantidade mínima de cada produto).

## Mensagens de contacto
As mensagens do formulário da loja aparecem em **Mensagens de contacto**.
- Escreva a resposta na conversa e envie: o cliente recebe-a por email.
- Quando o cliente responde a esse email, a resposta aparece na mesma conversa passado um ou
  dois minutos.

## Pedidos de dados pessoais (RGPD)
Se alguém pedir para ver ou apagar os seus dados (pelo formulário, assunto «Apagar os meus
dados»):
1. Confirme a identidade (responda para o email que está na mensagem).
2. Contacte o suporte técnico com o email da pessoa — o apagamento remove mensagens e pedidos
   de orçamento associados. Prazo legal: um mês.

As mensagens de contacto e os orçamentos terminados são apagados automaticamente ao fim de 24 meses.

## Utilizadores e permissões
| Perfil | Vê e edita |
|---|---|
| admin | tudo |
| catalog | categorias, modelos, cores, produtos |
| pedidos | orçamentos e encomendas |
| mensagens | mensagens de contacto |

Para criar utilizadores, mudar perfis ou repor palavras-passe, contacte o suporte.

## Suporte
Suporte técnico: Tomás Sousa — ver contrato de manutenção para contactos e prazos.
Estado do site: https://www.diomika.com/status.html
