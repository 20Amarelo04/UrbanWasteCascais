# Deploy da UrbanWasteCascais

Este projeto ja e uma aplicacao web Streamlit. Localmente corre com:

```powershell
streamlit run app.py
```

Para partilhar com outras pessoas, a opcao mais simples e publicar online.

## Opcao recomendada: Streamlit Community Cloud

### 1. Confirmar ficheiros essenciais

Na raiz do projeto devem existir:

```text
app.py
requirements.txt
config.py
core/
services/
solvers/
ui/
pages/
data/
```

O ficheiro `requirements.txt` deve incluir:

```text
streamlit>=1.36
pandas>=2.0
numpy>=1.24
plotly>=5.20
folium>=0.16
streamlit-folium>=0.20
ortools>=9.10
requests>=2.31
```

### 2. Criar repositorio no GitHub

1. Cria um repositorio no GitHub.
2. Faz upload da pasta completa `UrbanWasteCascais_FINAL`.
3. Confirma que a pasta `data/` tambem foi enviada, porque a app precisa das matrizes e do ficheiro `nodes.csv`.

### 3. Publicar no Streamlit Community Cloud

1. Entra em Streamlit Community Cloud.
2. Escolhe `New app`.
3. Seleciona o repositorio GitHub.
4. Define o ficheiro principal como:

```text
app.py
```

5. Faz deploy.

Depois do deploy, recebes um link publico para enviar aos testers.

## Testes antes de partilhar

Antes de enviar o link, confirma:

- A pagina `Inicio` abre sem erro.
- A pagina `Validacao dos dados` carrega os dados.
- A pagina `Otimizacao` corre pelo menos uma vez com OR-Tools.
- A pagina `Resultados` mostra mapa, tabelas e graficos.
- O modo Claro/Escuro funciona.
- A pagina `Ajuda` abre.

## Como pedir feedback aos testers

Sugestao de mensagem:

```text
Ola! Estou a testar uma app web para otimizacao de rotas de recolha urbana.

Podes abrir este link e tentar usar a app?

Queria que testasses:
- se consegues executar uma otimizacao;
- se o mapa aparece corretamente;
- se o modo claro/escuro funciona;
- se alguma coisa fica ilegivel;
- se aparece algum erro.

Se encontrares bug, envia-me:
1. o que fizeste;
2. que pagina estavas a usar;
3. print do erro ou do ecra;
4. se estavas em telemovel ou computador.
```

## Nota sobre dados privados

Se o repositorio GitHub for publico, os ficheiros do projeto tambem ficam publicos.
Se os dados forem sensiveis, usa um repositorio privado e uma plataforma que permita deploy a partir de repositorios privados.
