import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import subprocess  # Para executar comandos ADB
import re
import pandas as pd  # Para exportar relatório Excel
import datetime
import os

# Caminho do ADB (se o adb estiver no PATH do sistema, pode usar apenas "adb")
ADB_PATH = r"C:\Users\Administrador\adb\platform-tools\adb.exe"

# Variáveis globais
tempo_atual = 0
tempos = []
tensao = []
corrente = []
temperatura = []
bateria_percentual = []
ping_valores = []
ping_perdas = []   # <<< NOVA LISTA para perdas (%)

# Variáveis para os gráficos
ax1, ax2 = None, None
canvas = None

# Variável para armazenar o número de série
serial_atual = "Desconhecido"

# Função para mostrar dispositivos conectados
def mostrar_dispositivos():
    global serial_atual
    resultado = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True)
    dispositivos = [linha.split("\t")[0] for linha in resultado.stdout.splitlines() if "\tdevice" in linha]
    if dispositivos:
        serial_atual = dispositivos[0]
        messagebox.showinfo("Dispositivos ADB", "\n".join(dispositivos))
    else:
        serial_atual = "Nenhum dispositivo"
        messagebox.showinfo("Dispositivos ADB", "Nenhum dispositivo encontrado")

# Função para coletar dados
def coletar_dados():
    global tempo_atual

    # Dumpsys battery
    try:
        resultado_bateria = subprocess.run([ADB_PATH, "shell", "dumpsys", "battery"],
                                           capture_output=True, text=True)

        voltagem = re.search(r'voltage: (\d+)', resultado_bateria.stdout)
        corrente_val = re.search(r'current now: (-?\d+)', resultado_bateria.stdout)
        temp_val = re.search(r'temperature: (\d+)', resultado_bateria.stdout)
        perc_val = re.search(r'level: (\d+)', resultado_bateria.stdout)

        tensao_val = int(voltagem.group(1)) / 1000000 if voltagem else 0
        corrente_atual = int(corrente_val.group(1)) / 1000 if corrente_val else 0  # mA
        temp_celsius = int(temp_val.group(1)) / 10 if temp_val else 0  # décimos de °C
        perc_bateria = int(perc_val.group(1)) if perc_val else 0
    except Exception as e:
        tensao_val, corrente_atual, temp_celsius, perc_bateria = 0, 0, 0, 0
        print("Erro ao coletar bateria:", e)

    # Ping
    try:
        resultado_ping = subprocess.run([ADB_PATH, "shell", "ping -c 1 google.com"],
                                        capture_output=True, text=True)
        
        # Captura tempo (ms)
        ping_match = re.search(r'time=(\d+\.\d+)', resultado_ping.stdout)
        ping_valor = float(ping_match.group(1)) if ping_match else 0

        # Captura perdas (%)
        perda_match = re.search(r'(\d+)% packet loss', resultado_ping.stdout)
        perda_valor = int(perda_match.group(1)) if perda_match else 100  # se não achar, assume 100%
    except:
        ping_valor = 0
        perda_valor = 100

    # Atualiza listas
    tempo_atual += 1
    tempos.append(tempo_atual)
    tensao.append(tensao_val)
    corrente.append(corrente_atual)
    temperatura.append(temp_celsius)
    bateria_percentual.append(perc_bateria)
    ping_valores.append(ping_valor)
    ping_perdas.append(perda_valor)

# Atualiza os gráficos
def atualizar_dados():
    global ax1, ax2, canvas

    if ax1 is None or ax2 is None or canvas is None:
        return

    coletar_dados()

    # Limpa os dois gráficos
    ax1.clear()
    ax2.clear()

    # -------- CONFIG COMUM --------
    for ax in (ax1, ax2):
        ax.set_facecolor("black")
        ax.tick_params(colors="white", which="both")
        for spine in ax.spines.values():
            spine.set_color("white")
        ax.set_xlabel("Tempo (s)", color="white")
        ax.set_ylabel("Valores", color="white")
        ax.grid(True, color="white", linestyle="--", linewidth=0.7, alpha=0.7)

    # ----------- PLOTAGEM -----------
    # Gráfico 1: Energia
    ax1.plot(tempos, tensao, label="Tensão (V)", color="green")
    ax1.plot(tempos, corrente, label="Corrente (mA)", color="yellow")
    ax1.plot(tempos, temperatura, label="Temperatura (°C)", color="red")
    ax1.plot(tempos, bateria_percentual, label="Bateria (%)", color="white")
    ax1.set_title("Gráfico 1 - Energia", color="white")
    ax1.legend(loc="upper right", facecolor="black", edgecolor="white", labelcolor="white")

    # Gráfico 2: Rede 
    ax2.plot(tempos, ping_valores, label="Ping (ms)", color="magenta")
    ax2.plot(tempos, ping_perdas, label="Perda Pacotes (%)", color="red")
    ax2.set_title("Gráfico 2 - Rede", color="white")
    ax2.legend(loc="upper right", facecolor="black", edgecolor="white", labelcolor="white")

    # Atualiza no Tkinter
    canvas.draw_idle()
    root.after(2000, atualizar_dados)

# Inicia gráficos
def iniciar_grafico():
    global ax1, ax2, canvas

    fig, (ax1_local, ax2_local) = plt.subplots(1, 2, figsize=(12, 5))  # dois gráficos lado a lado

    # Configura fundo da figura
    fig.patch.set_facecolor("black")

    # Configurações iniciais para ambos
    for ax_local in (ax1_local, ax2_local):
        ax_local.set_facecolor("black")
        ax_local.tick_params(colors="white", which="both")
        ax_local.xaxis.label.set_color("white")
        ax_local.yaxis.label.set_color("white")
        ax_local.title.set_color("white")
        for spine in ax_local.spines.values():
            spine.set_color("white")
        ax_local.set_axisbelow(True)
        ax_local.grid(True, which="both", color="white", linestyle="--", linewidth=0.7, alpha=0.7, zorder=2)

    # Guarda os eixos
    ax1, ax2 = ax1_local, ax2_local
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().configure(bg="black", highlightthickness=0)
    canvas.get_tk_widget().pack()

    atualizar_dados()

# Extrair dados para Excel
def extrair_excel():
    dados = {
        "Tempo (s)": tempos,
        "Tensão (V)": tensao,
        "Corrente (mA)": corrente,
        "Temperatura (°C)": temperatura,
        "Bateria (%)": bateria_percentual,
        "Ping (ms)": ping_valores,
        "Perda Pacotes (%)": ping_perdas
    }
    df = pd.DataFrame(dados)

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    nome_arquivo = os.path.join(desktop, f"Relatorio_ADB_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    df.to_excel(nome_arquivo, index=False)
    messagebox.showinfo("Exportação concluída", f"Relatório salvo em:\n{nome_arquivo}")

# Interface Tkinter
root = tk.Tk()
root.title("Monitoramento ADB")
root.configure(bg="black")

btn_dispositivos = tk.Button(root, text="Mostrar Dispositivos", command=mostrar_dispositivos)
btn_dispositivos.pack(pady=5)

btn_grafico = tk.Button(root, text="Iniciar Gráficos", command=iniciar_grafico)
btn_grafico.pack(pady=5)

btn_excel = tk.Button(root, text="Extrair Dados", command=extrair_excel)
btn_excel.pack(pady=5)

root.mainloop()
