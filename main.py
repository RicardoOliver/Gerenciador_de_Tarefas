# main.py
import sys
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QListWidget, QLineEdit, QLabel, QHBoxLayout, QComboBox, QMessageBox, QDateEdit
from PySide6.QtCore import Qt, QTimer
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import threading

class TaskManager:
    def __init__(self):
        self.connection = sqlite3.connect("tasks.db")
        self.create_table()

    def create_table(self):
        with self.connection:
            # Removido para evitar a exclusão da tabela
            # self.connection.execute("DROP TABLE IF EXISTS tasks")  
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    status TEXT NOT NULL,
                    notification_type TEXT,
                    reminder_status TEXT DEFAULT 'Pendente'
                )
            """)

    def add_task(self, title, description, due_date, status, notification_type):
        with self.connection:
            self.connection.execute("INSERT INTO tasks (title, description, due_date, status, notification_type) VALUES (?, ?, ?, ?, ?)", (title, description, due_date, status, notification_type))

    def remove_task(self, task_id):
        with self.connection:
            self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def get_tasks(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, title, description, due_date, status, notification_type, reminder_status FROM tasks")
        return cursor.fetchall()

    def get_productivity_report(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT title, description, due_date, status FROM tasks")
        return cursor.fetchall()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador de Tarefas")
        self.setGeometry(100, 100, 800, 600)  # Aumentar a largura e altura

        # Inicializa o gerenciador de tarefas
        self.task_manager = TaskManager()

        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout principal
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Título
        self.title_label = QLabel("Gerenciador de Tarefas")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #333;")
        self.layout.addWidget(self.title_label)

        # Lista de tarefas
        self.task_list = QListWidget()
        self.layout.addWidget(self.task_list)

        # Layout para entrada de tarefa e botão
        self.input_layout = QHBoxLayout()
        self.layout.addLayout(self.input_layout)

        # Campo de entrada para título da tarefa
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Título da tarefa...")
        self.title_input.setFixedHeight(40)  # Aumenta a altura do campo
        self.input_layout.addWidget(self.title_input)

        # Campo de entrada para descrição da tarefa
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Descrição da tarefa...")
        self.description_input.setFixedHeight(40)  # Aumenta a altura do campo
        self.input_layout.addWidget(self.description_input)

        # Campo de entrada para prazo da tarefa
        self.due_date_input = QDateEdit()
        self.due_date_input.setDisplayFormat("dd/MM/yyyy")  # Formato mais amigável
        self.due_date_input.setCalendarPopup(True)  # Habilita o calendário pop-up
        self.due_date_input.setFixedHeight(40)  # Aumenta a altura do campo
        self.due_date_input.setFixedWidth(300)
        self.input_layout.addWidget(self.due_date_input)

        # ComboBox para status
        self.status_input = QComboBox()
        self.status_input.addItems(["Pendente", "Em Progresso", "Concluído"])
        self.status_input.setFixedHeight(40)  # Aumenta a altura do campo
        self.status_input.setFixedWidth(300)
        self.input_layout.addWidget(self.status_input)

        # ComboBox para tipo de notificação
        self.notification_type_input = QComboBox()
        self.notification_type_input.addItems(["E-mail"])  # Removido SMS
        self.notification_type_input.setFixedHeight(40)  # Aumenta a altura do campo
        self.notification_type_input.setFixedWidth(300)
        self.input_layout.addWidget(self.notification_type_input)

        # Botão para adicionar tarefa
        self.add_button = QPushButton("Adicionar Tarefa")
        self.add_button.clicked.connect(self.add_task)
        self.input_layout.addWidget(self.add_button)

        # Botão para remover tarefa
        self.remove_button = QPushButton("Remover Tarefa")
        self.remove_button.clicked.connect(self.remove_task)
        self.input_layout.addWidget(self.remove_button)

        # Botão para gerar relatório de produtividade
        self.report_button = QPushButton("Gerar Relatório de Produtividade")
        self.report_button.clicked.connect(self.generate_productivity_report)
        self.layout.addWidget(self.report_button)

        # Estilo
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            QLineEdit, QComboBox, QDateEdit {
                padding: 10px;
                font-size: 16px;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-right: 10px;  /* Adiciona espaço entre os campos */
            }
            QPushButton {
                padding: 10px;
                font-size: 16px;
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 5px;
                margin-left: 5px;  /* Adiciona espaço entre os botões */
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QListWidget {
                font-size: 16px;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-bottom: 10px;  /* Adiciona espaço abaixo da lista */
            }
        """)

        self.load_tasks()

        # Timer para verificar tarefas com prazos próximos
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_due_dates)
        self.timer.start(60000)  # Verifica a cada 60 segundos

    def load_tasks(self):
        self.task_list.clear()
        tasks = self.task_manager.get_tasks()
        for task_id, title, description, due_date, status, notification_type, reminder_status in tasks:
            self.task_list.addItem(f"{title} - {description} (Prazo: {due_date}, Status: {status}, Notificação: {notification_type}, Lembrete: {reminder_status}) (ID: {task_id})")

    def add_task(self):
        title_text = self.title_input.text()
        description_text = self.description_input.text()
        due_date_text = self.due_date_input.text()
        status_text = self.status_input.currentText()
        notification_type_text = self.notification_type_input.currentText()
        if title_text:
            self.task_manager.add_task(title_text, description_text, due_date_text, status_text, notification_type_text)
            self.load_tasks()
            self.title_input.clear()
            self.description_input.clear()
            self.due_date_input.clear()

    def remove_task(self):
        selected_item = self.task_list.currentItem()
        if selected_item:
            task_id = selected_item.text().split("(ID: ")[-1][:-1]  # Extrai o ID da tarefa
            self.task_manager.remove_task(task_id)
            self.load_tasks()
        else:
            QMessageBox.warning(self, "Aviso", "Selecione uma tarefa para remover.")

    def check_due_dates(self):
        tasks = self.task_manager.get_tasks()
        for task_id, title, description, due_date, status, notification_type, reminder_status in tasks:
            due_date_obj = datetime.strptime(due_date, "%d/%m/%Y")  # Corrigido para o formato correto
            if due_date_obj <= datetime.now() + timedelta(days=1) and status != "Concluído" and reminder_status == "Pendente":
                if notification_type == "E-mail":
                    self.send_email_notification(title, description, due_date)
                # Atualiza o status do lembrete para "Enviado"
                self.update_reminder_status(task_id)

    def update_reminder_status(self, task_id):
        with self.task_manager.connection:
            self.task_manager.connection.execute("UPDATE tasks SET reminder_status = 'Enviado' WHERE id = ?", (task_id,))

    def send_email_notification(self, title, description, due_date):
        def send_email():
            try:
                sender_email = "seuemailaqui@gmail.com"
                receiver_email = "emailaenviaraqui@gmail.com"
                password = "suasenhasmtpaqui"

                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = receiver_email
                msg['Subject'] = f"Lembrete: Tarefa '{title}' com prazo próximo"

                body = f"A tarefa '{title}' com descrição '{description}' tem prazo em {due_date}."
                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:  # Ajuste o timeout se necessário
                    server.starttls()
                    server.login(sender_email, password)
                    server.send_message(msg)
                print(f"Notificação de e-mail enviada para sobre a tarefa '{title}'.")
            except Exception as e:
                print(f"Erro ao enviar e-mail: {e}")

        # Inicia o envio de e-mail em uma nova thread
        email_thread = threading.Thread(target=send_email)
        email_thread.start()

    def generate_productivity_report(self):
        report = self.task_manager.get_productivity_report()
        pdf_file_path = "relatorio_produtividade.pdf"
        self.create_pdf_report(report, pdf_file_path)
        QMessageBox.information(self, "Relatório de Produtividade", f"Relatório gerado e salvo como {pdf_file_path}.")

    def create_pdf_report(self, report, file_path):
        c = canvas.Canvas(file_path, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Relatório de Produtividade")
        c.drawString(100, 730, f"Data: {datetime.now().strftime('%d/%m/%Y')}")
        c.drawString(100, 710, "Detalhes das Tarefas:")
        
        y_position = 690
        for title, description, due_date, status in report:
            c.drawString(100, y_position, f"Título: {title}, Descrição: {description}, Prazo: {due_date}, Status: {status}")
            y_position -= 20  # Espaço entre as linhas

        c.save()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())