
# Detecção de Veículos com IA

Este repositório contém o código-fonte e os recursos desenvolvidos para o projeto acadêmico de controle inteligente de tráfego, também conhecido como SmartPath (Semáforo Inteligente). O sistema propõe a automação e otimização do fluxo de veículos em cruzamentos por meio de Inteligência Artificial. A detecção é realizada em tempo real utilizando técnicas avançadas de Visão Computacional e Redes Neurais Convolucionais (modelo YOLOv8). 

### Estrutura do Sistema
A arquitetura do projeto foi desenhada sob o paradigma de microsserviços e processamento na borda (*Edge Computing*), dividindo-se nas seguintes frentes:
1. **Camada de Borda (Edge Computing):** Responsável pela captura de vídeo (câmeras de trânsito) e processamento inferencial local em Python para detecção de classes e volumes de veículos.
2. **Camada de Mensageria:** Emprega o RabbitMQ como *message broker* para garantir uma comunicação assíncrona, tolerante a falhas e de baixa latência entre a visão computacional e o *backend*.
3. **Camada de Microsserviços:** Ecossistema robusto em Java (Spring Boot, Spring Cloud, Eureka e API Gateway). O serviço central é o **Logic Controller**, que atua como cérebro da aplicação utilizando um Motor de Lógica Fuzzy para decidir dinamicamente os tempos dos semáforos.
4. **Camada de Dados:** Utiliza PostgreSQL para persistência do histórico do tráfego e métricas, em conjunto com o Redis (*cache* em memória) para acessos de altíssima performance aos estados mais recentes.

### 📊 Fluxo de Arquitetura

```mermaid
flowchart LR
    subgraph EdgeLayer ["📍 Camada de Borda (Python & Hardware)"]
        direction TB
        CAM[📷 Câmera / Vídeo] -->|Frames a 30 FPS| YOLO["🧠 Detecção (Python + YOLOv8)"]
        YOLO -->|Comando Serial| ARD["🚦 Arduino (Semáforo)"]
        YOLO -.->|WebSockets| DASH["📊 Web Dashboard"]
    end

    subgraph Messaging ["📨 Mensageria"]
        direction TB
        MQ(("🐇 RabbitMQ"))
    end

    subgraph CloudLayer ["☁️ Microsserviços (Java Spring Boot)"]
        direction TB
        EU["🌐 Eureka Server\n(Service Discovery)"]
        GW["🚪 API Gateway\n(Porta 8081)"]
        LC["⚙️ Logic Controller\n(Motor Fuzzy)"]

        EU -.->|Registra| GW
        EU -.->|Registra| LC
        GW -->|Roteamento REST| LC
    end

    subgraph DataLayer ["🗄️ Camada de Dados"]
        direction TB
        PG[("🐘 PostgreSQL\n(Histórico)")]
        RD[("⚡ Redis\n(Cache)")]
    end

    %% Fluxos principais
    YOLO -->|vehicle.detected\nemergency.alert| MQ
    MQ -->|Consome filas| LC
    LC -->|traffic.command\n(Decisão Fuzzy)| MQ
    MQ -->|Escuta comandos| YOLO

    LC -->|Persiste dados| PG
    LC <-->|Cache TTL 5m| RD
    DASH <-->|Configurações REST| GW

    %% Estilização base
    classDef python fill:#306998,stroke:#FFE873,stroke-width:2px,color:#fff;
    classDef java fill:#b07219,stroke:#fff,stroke-width:2px,color:#fff;
    classDef db fill:#336791,stroke:#fff,stroke-width:2px,color:#fff;
    classDef mq fill:#FF6600,stroke:#fff,stroke-width:2px,color:#fff;
    classDef dash fill:#00aba9,stroke:#fff,stroke-width:2px,color:#fff;
    classDef hardware fill:#00979d,stroke:#fff,stroke-width:2px,color:#fff;

    class YOLO python;
    class EU,GW,LC java;
    class PG,RD db;
    class MQ mq;
    class DASH dash;
    class ARD hardware;
```

## 💻 Stack Tecnológica

O ecossistema do projeto foi construído utilizando as seguintes tecnologias e frameworks:

*   **Inteligência Artificial e Visão Computacional:**
    *   **Python (3.10+):** Linguagem base para os scripts de processamento na borda.
    *   **YOLOv8 (Ultralytics):** Modelo de *Deep Learning* estado-da-arte para detecção e classificação de veículos em tempo real.
    *   **OpenCV:** Biblioteca utilizada para a manipulação dos frames e demarcação das regiões de interesse (ROIs).
*   **Arquitetura Back-end e Microsserviços:**
    *   **Java 17 & Spring Boot (3.x):** Base robusta e escalável para a orquestração das regras de negócio e Lógica Fuzzy.
    *   **Spring Cloud (Eureka & API Gateway):** Ferramentas para *Service Discovery* e roteamento inteligente das requisições REST.
*   **Mensageria e Persistência de Dados:**
    *   **RabbitMQ:** *Message broker* que garante a entrega de eventos assíncronos (desacoplamento entre IA e Back-end).
    *   **PostgreSQL:** Banco de dados relacional para o registro histórico do fluxo de tráfego.
    *   **Redis:** Armazenamento em memória (*cache*) para acesso ultrarrápido ao estado atual das vias.
*   **Hardware e Internet das Coisas (IoT):**
    *   **Arduino:** Microcontrolador responsável pelo acionamento físico dos semáforos, recebendo comandos via comunicação Serial.


## ⚙️ Instalação e Execução

Devido à natureza distribuída do sistema (arquitetura de microsserviços e processamento de borda), a inicialização do ambiente requer a configuração de diferentes módulos.

### 1. Pré-requisitos
Certifique-se de ter os seguintes componentes instalados em seu ambiente local:
- **Docker** (Recomendado para subir rapidamente os serviços de banco e mensageria)
- **Java JDK 17+** e **Maven** (Para os microsserviços Spring Boot)
- **Python 3.10+** (Para o módulo de Inteligência Artificial)

### 2. Infraestrutura (Dados e Mensageria)
Inicie os serviços de suporte: RabbitMQ (porta `5673`), PostgreSQL (porta `5433`) e Redis (porta `6379`). Se estiver utilizando Docker, você pode executá-los com:
```bash
docker run -d -p 5673:5672 -p 15672:15672 rabbitmq:3-management
docker run -d -p 5433:5432 -e POSTGRES_USER=smartpath -e POSTGRES_PASSWORD=smartpath123 postgres
docker run -d -p 6379:6379 redis
```

### 3. Microsserviços Java (Back-end)
Os microsserviços devem ser inicializados na seguinte ordem rigorosa para garantir o correto registro no *Service Discovery*:
1. **Eureka Server** (`porta 8761`)
2. **API Gateway** (`porta 8081`)
3. **Logic Controller** (`porta 8082`)

Navegue até o diretório de cada serviço e execute:
```bash
mvn spring-boot:run
```

### 4. Camada de Borda (Python & IA)
No diretório raiz do projeto, instale as dependências da visão computacional e inicie o nó de processamento:
```bash
# Instalação das bibliotecas necessárias
pip install ultralytics opencv-python pika pyserial websockets

# Execução do sistema de visão computacional
python DETECCAR_ARDUINO.py
```
    
## ✨ Funcionalidades

- **Visão Computacional em Tempo Real:** Detecção e classificação simultânea de múltiplas categorias de veículos (carros, motos, veículos pesados) e identificação de veículos de emergência (ambulâncias) utilizando YOLOv8.
- **Tomada de Decisão Inteligente (Lógica Fuzzy):** O Cérebro da aplicação (Back-end em Java) calcula dinamicamente o tempo ideal de abertura de cada semáforo com base no volume de tráfego atual e no tempo de espera (*starvation*).
- **Telemetria e Monitoramento:** Um *Dashboard Web* interativo atualizado via WebSockets exibe o streaming de vídeo processado, a contagem de veículos e o estado atual das vias.
- **Integração Física (IoT):** Comunicação em tempo real com microcontroladores (Arduino) para o acionamento físico dos relés que controlam as luzes dos semáforos reais.
- **Arquitetura Tolerante a Falhas:** Uso de filas no RabbitMQ garantindo que picos de processamento nos frames de vídeo não sobrecarreguem o sistema de tomada de decisão.


## 📚 Referências

Esta seção consolida as fontes de dados, bibliotecas de software e literaturas científicas que embasaram o desenvolvimento tecnológico e teórico do **SmartPath**.

### Conjunto de Dados (Dataset) e Código Auxiliar
- **Base Experimental (Kaggle):** [Real-Time Traffic Density Estimation with YOLOv8](https://www.kaggle.com/code/farzadnekouei/real-time-traffic-density-estimation-with-yolov8) — *Referência fundamental para o fluxo inicial de pipeline e modelagem visual.*

### Principais Bibliotecas e Frameworks
- **Inteligência Artificial & Visão:** [Ultralytics (YOLOv8)](https://github.com/ultralytics/ultralytics) | [OpenCV](https://github.com/opencv/opencv)
- **Ecossistema Back-end:** [Spring Boot & Spring Cloud](https://spring.io/) | [RabbitMQ](https://www.rabbitmq.com/)

### Trabalhos Correlatos e Fundamentação Teórica
Os artigos abaixo serviram como alicerce acadêmico para a escolha de heurísticas de controle e modelagem de tráfego em cidades inteligentes:
1. *[An intelligent control system for traffic lights with simulation-based evaluation](https://www.sciencedirect.com/science/article/abs/pii/S096706611630212X)*
2. *[Internet of smart-cameras for traffic lights optimization in smart cities](https://www.sciencedirect.com/science/article/pii/S2542660520300433)*
