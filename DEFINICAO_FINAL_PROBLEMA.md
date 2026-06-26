# Definição Final do Problema

## Objetivo

Desenvolver um sistema de apoio à decisão para a otimização de rotas
de recolha de resíduos urbanos em Cascais.

O sistema deve maximizar o número de contentores recolhidos e, entre
soluções que recolhem o mesmo número de contentores, minimizar
simultaneamente:

- distância total percorrida;
- duração total das rotas;
- consumo total de combustível.

## Função objetivo

A avaliação das soluções utiliza uma combinação normalizada:

C = wd × Dnorm + wt × Tnorm + wf × Fnorm

Onde:

- Dnorm representa a distância normalizada;
- Tnorm representa o tempo normalizado;
- Fnorm representa o consumo normalizado;
- wd, wt e wf representam os pesos dos três critérios.

Pesos iniciais:

- distância: 0,30;
- tempo: 0,30;
- combustível: 0,40.

A soma dos pesos deve ser igual a 1.

## Prioridade das soluções

As soluções são comparadas pela seguinte ordem:

1. maior número de contentores recolhidos;
2. menor valor da função objetivo;
3. menor consumo;
4. menor tempo;
5. menor distância.

## Restrições

Cada rota deve:

- começar na base;
- terminar na base;
- respeitar a duração máxima do turno;
- respeitar a capacidade do veículo;
- passar pelo aterro quando for necessário descarregar;
- contabilizar o tempo de serviço em cada contentor;
- contabilizar o tempo de descarga no aterro;
- impedir que o mesmo contentor seja recolhido mais do que uma vez;
- recalcular o consumo de acordo com a massa atual do veículo.

## Nós especiais

- nó 0: base;
- nó 1: aterro;
- restantes nós: contentores.

## Parâmetros operacionais iniciais

- duração máxima do turno: 28 800 segundos;
- capacidade inicial do veículo: 9 000 kg;
- tara inicial do veículo: 6 000 kg;
- duração da descarga no aterro: 1 800 segundos.

Os parâmetros podem ser alterados na interface de acordo com o veículo.

## Dados utilizados

- rede rodoviária obtida através do OSMnx;
- matriz de distâncias em metros;
- matriz de tempos em segundos;
- dados dos contentores;
- características dos veículos;
- modelo dinâmico de consumo de combustível.

## Algoritmos

A aplicação disponibiliza:

- OR-Tools;
- MMAS, Max-Min Ant System.

O MMAS mantém a melhor solução global encontrada durante as suas
iterações, mas não garante matematicamente o ótimo global.

## Saídas

Para cada otimização devem ser apresentados:

- rotas de cada veículo;
- contentores recolhidos;
- contentores não recolhidos;
- distância total;
- duração total;
- consumo total;
- quantidade de resíduos recolhida;
- número de deslocações ao aterro;
- mapa das rotas;
- tempo de execução do algoritmo.