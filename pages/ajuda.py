from __future__ import annotations

import streamlit as st

from ui.theme import info_card, page_header


page_header(
    title="Ajuda",
    subtitle=(
        "Guia rápido para perceber os parâmetros da otimização "
        "e interpretar os resultados sem mexer às cegas."
    ),
    label="Manual da aplicação",
)

st.info(
    "Dica: quase todos os campos da página Otimização têm um ícone "
    "de ajuda. Passa o rato por cima para veres uma explicação rápida."
)

section = st.radio(
    "O que queres perceber?",
    options=[
        "Configuração",
        "Algoritmos",
        "Função objetivo",
        "Resultados",
        "Mapa",
    ],
    index=0,
    horizontal=True,
)

if section == "Configuração":
    st.subheader("Configuração da operação")

    st.markdown(
        """
        | Campo | O que significa | Impacto prático |
        |---|---|---|
        | Número de veículos | Quantos camiões estão disponíveis | Mais veículos podem reduzir duração, mas podem aumentar distância total |
        | Carga por contentor | Peso estimado recolhido em cada contentor | Afeta capacidade, descargas e combustível |
        | Tempo de serviço | Tempo parado em cada recolha | Aumenta a duração total da rota |
        | Tempo de descarga | Tempo gasto no aterro | Penaliza rotas com muitas descargas |
        | Máximo de descargas | Limite de idas ao aterro por veículo | Controla se um veículo pode continuar após encher |
        """
    )

    left, right = st.columns(2)

    with left:
        info_card(
            title="Quando aumentar veículos?",
            body=(
                "Quando a operação excede o turno, há contentores por "
                "recolher ou uma rota fica demasiado longa."
            ),
            badge="Frota",
        )

    with right:
        info_card(
            title="Quando ajustar descargas?",
            body=(
                "Quando o camião enche antes de terminar a rota. "
                "Mais descargas dão flexibilidade, mas consomem tempo."
            ),
            badge="Operação",
        )

elif section == "Algoritmos":
    st.subheader("OR-Tools vs MMAS")

    st.markdown(
        """
        | Algoritmo | Quando usar | O que esperar |
        |---|---|---|
        | OR-Tools | Testes rápidos e soluções estáveis | Normalmente mais previsível e rápido |
        | MMAS | Exploração experimental de alternativas | Pode encontrar soluções interessantes, mas depende dos parâmetros |
        """
    )

    st.warning(
        "O OR-Tools pode usar só parte da frota se isso for melhor para "
        "a função objetivo. Isso não é necessariamente erro."
    )

    st.markdown(
        """
        **Parâmetros MMAS importantes**

        - `Número de formigas`: quantas soluções são testadas por iteração.
        - `Número de iterações`: durante quanto tempo a procura evolui.
        - `Lista de candidatos`: quantos contentores próximos são considerados em cada decisão.
        - `Formigas elite`: quantas boas soluções reforçam os melhores caminhos.
        - `Limite de estagnação`: quando a procura fica presa, força renovação.
        """
    )

elif section == "Função objetivo":
    st.subheader("Função objetivo")

    st.write(
        "A função objetivo decide o que significa uma rota ser melhor. "
        "Os três pesos são normalizados automaticamente."
    )

    st.markdown(
        """
        | Peso | Se aumentares | Possível efeito |
        |---|---|---|
        | Distância | O solver evita quilómetros | Pode aceitar rotas mais demoradas |
        | Tempo | O solver reduz duração operacional | Pode aumentar distância ou combustível |
        | Combustível | O solver evita consumo, massa e declives | Pode escolher caminhos menos óbvios |
        """
    )

    st.success(
        "Neste projeto, o combustível usa distância, tempo, massa do veículo, "
        "carga transportada e declive entre pontos."
    )

elif section == "Resultados":
    st.subheader("Como ler os resultados")

    st.markdown(
        """
        | Métrica | Como interpretar |
        |---|---|
        | Contentores recolhidos | Quantos contentores entraram nas rotas |
        | Não recolhidos | Contentores que ficaram fora da solução |
        | Distância total | Soma dos quilómetros de todos os veículos |
        | Maior rota | Duração do veículo que acabou mais tarde |
        | Combustível | Estimativa total de litros consumidos |
        | Score | Valor da função objetivo; menor tende a ser melhor |
        | Solução viável | Indica se respeita capacidade, turno, descargas e regras de rota |
        """
    )

    st.warning(
        "Uma solução pode recolher tudo, mas ainda não ser a melhor se gastar "
        "muito tempo, distância ou combustível."
    )

elif section == "Mapa":
    st.subheader("Mapa interativo")

    st.markdown(
        """
        | Controlo | Para que serve |
        |---|---|
        | Veículos visíveis | Mostra ou esconde rotas por veículo |
        | Rota pelas estradas | Troca linha direta por geometria real via OSRM |
        | Não recolhidos | Mostra contentores fora da solução a cinza |
        | Camadas Folium | Permite ligar/desligar veículos e pontos no mapa |
        """
    )

    st.info(
        "Se o serviço OSRM falhar ou estiver lento, a app continua a mostrar "
        "a rota em linha direta como fallback."
    )
