const int pinoVermelho = 10;
const int pinoAmarelo = 9;
const int pinoVerde = 8;

void setup() {
  // Inicia a comunicação Serial a 9600 bps
  Serial.begin(9600);
  
  // Configura os pinos como saída
  pinMode(pinoVermelho, OUTPUT);
  pinMode(pinoAmarelo, OUTPUT);
  pinMode(pinoVerde, OUTPUT);
  
  // Estado inicial: Semáforo Vermelho
  digitalWrite(pinoVermelho, HIGH);
  digitalWrite(pinoAmarelo, LOW);
  digitalWrite(pinoVerde, LOW);
  
  Serial.println("Semaforo Pronto. Aguardando comando via Python...");
}

void loop() {
  // Verifica se há dados disponíveis na porta Serial
  if (Serial.available() > 0) {
    // Lê a string até encontrar uma quebra de linha
    String comando = Serial.readStringUntil('\n');
    comando.trim(); // Remove espaços em branco ou caracteres especiais extras
    
    // Verifica se o comando é para abrir o sinal Verde (ex: "G:25")
    if (comando.startsWith("G:")) {
      // Extrai os segundos do comando
      int tempoVerdeS = comando.substring(2).toInt();
      
      if (tempoVerdeS > 0) {
        // === Início da Sequência do Semáforo ===
        
        // 1. Apaga o Vermelho e acende o Verde
        digitalWrite(pinoVermelho, LOW);
        digitalWrite(pinoVerde, HIGH);
        
        // Aguarda o tempo de verde estipulado pelo Python
        // (Multiplica por 1000 porque o delay do Arduino é em milissegundos)
        delay(tempoVerdeS * 1000UL); 
        
        // 2. Apaga o Verde e acende o Amarelo
        digitalWrite(pinoVerde, LOW);
        digitalWrite(pinoAmarelo, HIGH);
        
        // Aguarda 3 segundos para o amarelo
        delay(3000); 
        
        // 3. Apaga o Amarelo e volta para o Vermelho
        digitalWrite(pinoAmarelo, LOW);
        digitalWrite(pinoVermelho, HIGH);
        
        // === Fim da Sequência ===
        
        // Envia mensagem de volta para o Python informando que terminou
        // Isso avisa o Python que o Arduino está pronto para receber um novo comando
        Serial.println("CICLO_COMPLETO");
      }
    }
  }
}
