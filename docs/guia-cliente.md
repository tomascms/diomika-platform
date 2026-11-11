# Guia do backoffice Diomika

O backoffice é a aplicação onde gere o catálogo da loja, os orçamentos, as encomendas e as
mensagens de contacto. Funciona em Windows e Mac e liga-se sozinho a `api.diomika.com`.

## Instalar e entrar

1. Instale com o ficheiro que recebeu (`Diomika-Backoffice-<versão>-setup.exe` no Windows,
   `.dmg` no Mac). Se o Windows avisar «Editor desconhecido», escolha
   **Mais informações → Executar mesmo assim** (a aplicação não tem certificado pago).
2. Abra a aplicação: entra sozinha, sem utilizador nem palavra-passe. Não dê o instalador a ninguém:
   quem o tiver entra no backoffice.

**No Mac, só na primeira vez** (a aplicação não tem a assinatura paga da Apple):

1. Abra o `.dmg` e arraste **Diomika Backoffice** para a pasta **Aplicações**.
2. Abra a aplicação. O Mac diz que não a pode verificar: carregue em **OK** (ou **Concluído**).
3. Abra **Definições do Sistema → Privacidade e Segurança**, desça até ao fim e carregue em
   **Abrir mesmo assim**. Confirme com a palavra-passe do Mac.
4. Se o antivírus bloquear o ficheiro, autorize «Diomika Backoffice» no antivírus.

A partir daí abre normalmente.

**Actualizações:** a aplicação não se actualiza sozinha. As mudanças no servidor (dados, regras, orçamentos) chegam sem fazer nada, mas quando os
ecrãs da aplicação mudam a Diomika envia um instalador novo. Instale-o por cima
do anterior; os dados não se perdem, estão no servidor.

## Catálogo

O catálogo organiza-se em **família de produto** (ex.: Almofadas) → **categoria**
(ex.: Almofadas de Natal) → **modelo** → **cores** e **produtos (EAN)**.

### Criar uma categoria
Em **Categorias → + Nova**, escolha a família e o nome. A família define os campos que os
modelos vão ter (tipo, dimensões, composição…).
A **Quantidade mínima** vale para todos os artigos da categoria e é também o passo do pedido
(12 → 12, 24, 36…).

### Criar um modelo e pô-lo na loja
1. Na categoria, **+ Adicionar** um modelo e **Guardar rascunho**. Fica oculto na loja.
2. Em **Cores do modelo**, **+ Adicionar cor** com número, nome e imagem.
3. Em **Produtos (EAN)**, **+ Adicionar produto** com o EAN-13 e a medida/altura.
4. Carregue em **Publicar na loja**. A aplicação recusa se faltar pelo menos uma cor com
   imagem ou um produto com EAN — a mensagem diz o que falta.

Regras:
- O **EAN é único em todo o catálogo**: não pode repetir-se entre famílias.
- No **Material de Cozinha** e no **Regional**, em **Novo registo** escolhe-se a categoria e depois a subcategoria
  (avental, luva, pega, pano de cozinha…); só então abre o formulário.
- **Ocultar** tira o modelo da loja sem o apagar.
- A loja mostra as alterações em segundos (a cache é renovada a cada gravação).

### Exportar e importar
Em cada lista, **Exportar CSV** descarrega os registos. A importação de CSV mostra primeiro
uma pré-visualização e só grava depois de confirmar.

## Orçamentos do site
Os pedidos feitos na loja aparecem em **Orçamentos do site**. Abra um para ver as linhas e
descarregar o PDF. As linhas mostram o nome do modelo, a medida e a cor, e o pedido mostra por onde o
comprador entrou no site.

Em **Ciclo do pedido** mude o **estado** à medida que avança com o cliente: Nova → Em análise → Proposta enviada
→ Ganho (vendido) / Perdido / Arquivado. Pode registar o **valor da proposta** e uma **nota interna** (o cliente
não a vê). Ao marcar **Ganho** fica guardada a data da venda, e esse pedido nunca é apagado pela retenção dos
24 meses; os pedidos sem venda são apagados passado esse prazo.

**Responder por email** abre o seu programa de email com um de dois textos já escritos: **Proposta a particular**
(leva a informação que a lei exige antes de o particular aceitar e pede que responda «Aceito» por escrito) e
**Confirmação de encomenda** (a enviar no prazo de 5 dias depois de aceite). Preencha o que está entre
[parênteses] e anexe o PDF. Envie sempre as condições gerais de venda com a proposta. Uma venda a particular só
fica fechada com o «Aceito» escrito; por telefone não basta.

Cada pedido tem um número («Pedido n.º …»): é o que o comprador vê no ecrã de confirmação e pode indicar
no WhatsApp ou ao telefone. Se o comprador os indicou, o pedido mostra também a empresa, o NIF, a localidade
e se compra como empresa ou como particular; a um particular aplicam-se os direitos de consumidor (parte B2C
das condições gerais de venda).

## Conteúdo em falta
No menu, **Conteúdo em falta** lista os modelos com algo por preencher (descrição, composição, EAN, fotografia
real, mais do que a cor «Sortido»), com uma ligação para cada um. Ao escolher uma fotografia, a aplicação avisa
se tem menos de 1200 px de lado ou se não é quase quadrada (a loja mostra-a num quadrado).

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
