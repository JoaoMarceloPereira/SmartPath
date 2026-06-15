
# Detecção de Veículos com IA

Este repositório contém o código-fonte e os recursos necessários para um projeto de detecção de veículos utilizando Inteligência Artificial. A detecção é realizada por meio da combinação de técnicas de Visão Computacional e Redes Neurais Convolucionais (CNN). Como o GitHub não permiti que carregue mais de 100 arquivos de uma vez e que o tamanho limite é de 15 TB, estarei deixando na secção de Referências o link do Dropbox com as imagens utilizadas para treinar a IA. 

   - **Logic Controller:** Cérebro da aplicação contendo o motor Fuzzy.
4. **Camada de Dados:** PostgreSQL para armazenamento de histórico persistente e Redis para cache de altíssima velocidade.

### 📊 Fluxo de Arquitetura

```mermaid
graph TD
    subgraph Edge Layer [Camada de Borda - Python]
        C[Câmera/Vídeo] -->|Frames a 30 FPS| P[Python + YOLOv8]
        P -->|Comando Serial| A[Arduino / Semáforo Físico]
    end

    subgraph Messaging Layer [Mensageria]
        MQ((RabbitMQ))
    end

    subgraph Microservices Layer [Microsserviços - Java Spring Boot]
        EU[Eureka Server\nService Discovery]
        GW[API Gateway\nPorta 8081]
        LC[Logic Controller\nMotor Fuzzy]

        EU -.->|Registra| GW
        EU -.->|Registra| LC
    end

    subgraph Data Layer [Camada de Dados]
        PG[(PostgreSQL\nHistórico)]
        RD[(Redis\nCache)]
    end

    %% Fluxos principais
    P -->|vehicle.detected\nemergency.alert| MQ
    MQ -->|Consome| LC
    LC -->|Calcula Pressão\ntraffic.command| MQ
    MQ -->|Escuta Decisão| P
    LC -->|Salva Histórico| PG
    LC -->|Cache (TTL 5m)| RD
    P -.->|WebSockets Telemetria| DB[Web Dashboard]
    DB <-->|Ajustes REST| GW
    GW -->|Roteamento| LC
```

## 💻 Stack Tecnológica

*   **IA e Visão:** Python 3.10+, OpenCV, Ultralytics (YOLOv8)


## 🎥 Demonstração simples

<div align="center">
  <img src="https://github.com/pedrofratassi/identificacao-veiculos/blob/main/static/demo.gif"/>
</div>


## Stack utilizada

**Front-end:** Google Colab

**Back-end:** OpenCV, YOLO e Ultralytics

```
## Instalação

Instalação necessária para rodar o código:

```bash
# -*- coding: utf-8 -*-
"""DETECCAR: Detecção de Veículos e Controle de Semáforos Inteligentes com YOLOv8"""

# 📌 Importação das bibliotecas necessárias
import os
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import random
import warnings
import yaml
from PIL import Image
from ultralytics import YOLO
from IPython.display import Video, display

warnings.filterwarnings('ignore')  # Removendo avisos desnecessários

# 📌 Configuração do Seaborn para visualização de gráficos
sns.set(rc={'axes.facecolor': '#eae8fa'}, style='darkgrid')
```
    
## Funcionalidades

- Detecção de veículos
- Detecção de veículos em tempo-real


## Aprendizados

O projeto Semáforo Inteligente foi um grande desafio e uma grande fonte de estímulo para o aprendizado e reflexão, empregando grande parte dos conhecimentos adquiridos ao longo do curso de Tecnologia em Análise e Desenvolvimento de Sistemas.


## Melhorias para Trabalhos  Futuros

Em perspectiva futuras atualizações do software, manifesta-se a possibilidade em ampliar a capacidade do sistema para detectar não somente veículos, mas também de pedestres. Planeja-se também a implementação do método para o controle da via. Outro ponto relevante para evolução é a introdução de câmeras inteligentes e sensores no sistema, visando o aprimoramento do software para poder ser utilizando em situação real de controle de tráfego de veículos e pedestres. As incorporações tecnológicas proporcionarão uma perspectiva mais ampla e aprofundada do ambiente, permitindo ajustes dinâmicos e eficientes nas condições do tráfego de veículos.


## Referências
Nesta seção, você encontrará a fonte dos dados como os códigos e bibliotecas que foram utilizados neste projeto. 

### Bibliotecas Utilizadas
 - [OpenCV](https://github.com/opencv/opencv)
 - [YOLO](https://github.com/AlexeyAB/darknet)
 - [Ultralytics](https://github.com/ultralytics/ultralytics)

### Trabalhos Correlatos
Esta subseção apresenta alguns trabalhos que foram utilizados como referência para o desenvolvimento deste trabalho. Estes trabalhos contribuíram para a escolha de alguns conceitos, tecnologias ou técnicas, que foram utilizados neste trabalho.

- [An intelligent control system for traffic lights with simulation-based evaluation](https://www.sciencedirect.com/science/article/abs/pii/S096706611630212X)

 - [Internet of smart-cameras for traffic lights optimization in smart cities](https://www.sciencedirect.com/science/article/pii/S2542660520300433)

### Fonte dos Dados e Código Utilizado
 - [Real-Time Traffic Density Estimation with YOLOv8](https://www.kaggle.com/code/farzadnekouei/real-time-traffic-density-estimation-with-yolov8)

Este conjunto de dados e código foram fundamentais para o desenvolvimento e treinamento do modelo de detecção de veículos neste projeto.

## Licença

[MIT](https://choosealicense.com/licenses/mit/)


## Autores

- [@pedrofratassi](https://github.com/pedrofratassi)

