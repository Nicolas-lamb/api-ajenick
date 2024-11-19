from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import bcrypt
import random
import string

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
    # Obter os parâmetros opcionais
    palavra_chave = request.args.get('nome', default=None)
    materia = request.args.get('materia', default=None)
    id_usuario = request.args.get('id_usuario', default=None)
    print(id_usuario)
    # Conectar ao banco de dados

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    # Construir a query dinamicamente
    query = "SELECT nome, descricao, id_jogo, id_usuario, materia, codigo FROM jogo WHERE 1=1"
    params = []

    if palavra_chave:
        query += " AND nome ILIKE %s OR codigo = %s"
        params.append(f"%{palavra_chave}%")
        params.append(palavra_chave)

        query += " OR similarity(nome, %s) > 0.3"  # Você pode ajustar o valor de 0.3 conforme necessário
        params.append(palavra_chave)

    if materia and materia != "Nenhuma":
        query += " AND materia ILIKE %s"
        params.append(f"%{materia}%")

    if id_usuario:
        query += " AND id_usuario = %s"
        params.append(id_usuario)  

    # Executar a query
    cursor.execute(query, params)
    rows = cursor.fetchall()
    # Fechar a conexão
    cursor.close()
    conn.close()
    return jsonify(rows)

@app.route('/get_game_details', methods=['GET'])
def get_game_details():
    id_jogo = request.args.get('id_jogo')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Busca os detalhes do jogo e o nome do criador
    query = """
        SELECT j.nome, j.materia, j.codigo, j.descricao, u.nome AS nome_criador, j.id_jogo, j.id_usuario
        FROM jogo j
        INNER JOIN usuario u ON j.id_usuario = u.id_usuario
        WHERE j.id_jogo = %s
    """
    cursor.execute(query, (id_jogo,))
    result = cursor.fetchone()
    
    conn.close()

    if result:
        return jsonify({
            "nome": result[0],
            "materia": result[1],
            "codigo": result[2],
            "descricao": result[3],
            "nomeCriador": result[4],
            "id_jogo": result[5],
            "id_criador": result[6]
        })
    else:
        return jsonify({"error": "Jogo não encontrado"}), 404


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

@app.route('/get_user', methods=['GET'])
def get_user():
    # Obter o ID do usuário (assumindo que você está passando como parâmetro na URL)
    id_usuario = request.args.get('id_usuario', type=int)

    if not id_usuario:
        return jsonify({"error": "ID do usuário não fornecido"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Consultar o banco de dados
        query = "SELECT nome, descricao FROM usuario WHERE id_usuario = %s"
        cursor.execute(query, (id_usuario,))
        user_data = cursor.fetchone()

        if not user_data:
            return jsonify({"error": "Usuário não encontrado"}), 404

        return jsonify(user_data)
    finally:
        cursor.close()
        conn.close()


@app.route('/add_game', methods=['POST'])
def add_game():
    def generate_unique_code():
        """Gera um código único de 8 caracteres."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    data = request.get_json()
    nome = data['Titulo']
    descricao = data['Descricao']
    materia = data['Materia']
    id_usuario = data['Usuario']
    print(materia)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Gera e valida o código único
    unique_code = generate_unique_code()
    while True:
        cursor.execute("SELECT 1 FROM jogo WHERE codigo = %s", (unique_code,))
        if not cursor.fetchone():
            break  # Código é único, pode sair do loop
        unique_code = generate_unique_code()

    # Insere o jogo no banco de dados
    cursor.execute(
        "INSERT INTO jogo (nome, descricao, id_usuario, materia, codigo) VALUES (%s, %s, %s, %s, %s) RETURNING id_jogo",
        (nome, descricao, id_usuario, materia, unique_code)
    )
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



# Rota para registrar um novo usuário
@app.route('/register', methods=['POST'])
def register_user():
      # Mostra dados recebidos no log para debug
    data = request.get_json()
    print("Dados recebidos:", data)

    # Validação para garantir que todos os campos foram enviados
    if 'Email' not in data or 'Senha' not in data or 'Nome' not in data:
        print("Erro: Dados incompletos")
        return jsonify({'error': 'Dados incompletos'}), 400

    # Acessa os dados
    email = data['Email']
    senha = data['Senha']
    nome = data['Nome']

    # Criptografa a senha com bcrypt
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    print("Senha criptografada:", senha_hash)

    try:
        # Conexão com o banco de dados
        conn = get_db_connection()
        print("Conexão com o banco estabelecida")
        
        cursor = conn.cursor()
        print("Cursor criado com sucesso")

        # Teste de Inserção
        cursor.execute(
            "INSERT INTO usuario (email, senha, nome) VALUES (%s, %s, %s) RETURNING id_usuario",
            (email, senha_hash.decode('utf-8'), nome)
        )
        id_usuario = cursor.fetchone()[0]
        conn.commit()

        # Fecha a conexão
        cursor.close()
        conn.close()

        return jsonify({'id_usuario': id_usuario}), 201

    except Exception as e:
        print("Erro ao registrar usuário:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    print("Dados recebidos:", data)

    email = data.get('Email')
    senha = data.get('Senha')

    if not email or not senha:
        return jsonify({"error": "Email e senha são obrigatórios"}), 400

    try:
        # Estabelecendo conexão com o banco
        conn = get_db_connection()
        print("Conexão com o banco estabelecida")

        # Criando o cursor
        cursor = conn.cursor()
        print("Cursor criado com sucesso")

        # Executando a consulta
        cursor.execute("SELECT id_usuario, senha FROM usuario WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        print("Resultado da consulta:", usuario)

        if usuario is None:
            return jsonify({"error": "Usuário não encontrado"}), 404

        # Recuperando o ID e a senha armazenada
        id_usuario, senha_armazenada = usuario

        # Verificando a senha usando bcrypt.checkpw
        if bcrypt.checkpw(senha.encode('utf-8'), senha_armazenada.encode('utf-8')):
            print(f"Login bem-sucedido para o usuário: {id_usuario}")
            return jsonify({"id_usuario": id_usuario}), 200
        else:
            print("Senha incorreta")
            return jsonify({"error": "Senha incorreta"}), 401

    except Exception as e:
        print("Erro no servidor:", str(e))
        return jsonify({"error": "Erro interno no servidor"}), 500

    finally:
        if 'cursor' in locals():  # Fecha o cursor apenas se ele foi criado
            cursor.close()
        if 'conn' in locals():  # Fecha a conexão apenas se ela foi criada
            conn.close()

if __name__ == '__main__':
 app.run(host='0.0.0.0', port=6000, debug=True)
