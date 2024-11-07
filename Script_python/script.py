from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

# Configurações do banco de dados PostgreSQL
db_config = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
}

# Função para conectar ao banco PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(**db_config)
    return conn

# Rota para buscar os itens
@app.route('/get_items', methods=['GET'])
def get_items():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT nome, descricao, id_jogo FROM jogo")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

# Rota para buscar perguntas com base no id_jogo
@app.route('/get_questions', methods=['GET'])
def get_questions():
    id_jogo = request.args.get('id_jogo')
    if not id_jogo:
        return jsonify({'error': 'id_jogo não fornecido'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM pergunta WHERE id_jogo = %s", (id_jogo,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

@app.route('/add_game', methods=['POST'])
def add_game():
    data = request.get_json()
    nome = data['Titulo']
    descricao = data['Descricao']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jogo (nome, descricao, id_usuario) VALUES (%s, %s, 1) RETURNING id_jogo", (nome, descricao))
    id_jogo = cursor.fetchone()[0]  # Obtém o id_jogo gerado
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify(id_jogo)

@app.route('/add_questions', methods=['POST'])
def add_questions():
    data = request.get_json()
    perguntas = data['perguntas']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for pergunta in perguntas:
        cursor.execute("""
            INSERT INTO pergunta (questao, alternativa1, alternativa2, alternativa3, alternativa4, resposta, id_jogo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (pergunta['questao'], pergunta['alternativa1'], pergunta['alternativa2'], pergunta['alternativa3'],
              pergunta['alternativa4'], pergunta['indexRes'], pergunta['id_jogo']))
    
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
