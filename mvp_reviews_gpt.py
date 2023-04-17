#### MVP - PULSE GPT
import streamlit as st
import pandas as pd
import numpy as np
import xlsxwriter
import requests
import json
import base64
from io import BytesIO

# Função para transformar df em excel
def to_excel(df):
	output = BytesIO()
	writer = pd.ExcelWriter(output, engine='xlsxwriter')
	df.to_excel(writer, sheet_name='Planilha1',index=False)
	writer.save()
	processed_data = output.getvalue()
	return processed_data
	
# Função para gerar link de download
def get_table_download_link(df):
	val = to_excel(df)
	b64 = base64.b64encode(val)
	return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="extract.xlsx">Download</a>'

st.title("Pulse GPT")
st.write('Esta aplicação tem como objetivo auxiliar o time de atendimento de Pulse Solution com respostas geradas por IA')
st.write()

# Inserindo Review Sheet
reviewSheet = st.file_uploader("Insira um arquivo .xlsx da Review Sheet")

df = pd.read_excel(reviewSheet)
st.write(df.head())


st.subheader('Parâmetros do prompt')

########## Informações do cliente ########## 
nomeApp = st.text_input('Insira o nome que chamaremos o app ao responder')
voz = st.selectbox('Selecione o tom de voz', ('Neutro','Informal', 'Formal'))
pessoa = ('1ª pessoa do plural','1ª pessoa do singular (masculino)','1ª pessoa do singular (feminino)','2ª pessoa','3ª pessoa')
pessoaVerbal = st.selectbox('Selecione a pessoa verbal', pessoa)
evitar = st.text_input('Informe o que deve ser evitado na resposta (cada item deve ser separado por vírgula)')
contato = st.text_input('Insira a forma de contato para o cliente')

########## Criação do prompt ########## 

def primeiro_nome(nome):
    nome_split = nome.split(' ')
    if len(nome_split) > 1:
        return nome_split[0]
    else:
        return 'Nenhum'

def createPrompt(sentiment,rating, voz, pessoaVerbal, nomeApp, evitar, contato):
	infos = f'''Tom de voz: {voz} na {pessoaVerbal}  
	\nNome do aplicativo: {nomeApp}
	\nEvitar: {evitar}
	\nContato: {contato}'''

	prompt = f"""Haja como um atendente de um aplicativo que responde os comentários dos usuários.
	Sempre inicie a resposta com uma saudação ao cliente! 
	Cada resposta deve seguir às seguintes instruções: 
	para comentário de sentimento positivo, responda de forma que agradeça o usuário e 
	para cada comentário de sentimento negativo, responda se desculpando. 
	Para a nota de 1 a 5, considere 1 como Muito Insatisfeito e 5 como Muito Satisfeito.
	Responda com o tom de voz selecionado. Insira o contato. Evite o que for fornecido nas instruções. 
	Sempre use a expressão 'app' ou 'aplicativo' antes de se referir ao nome do aplicativo. 
	\n{infos} 
	\nSentimento: {sentiment}
	\nRating: {rating}
	\nMáximo de caracteres na resposta: 300"""

	return prompt


dfPrompt = df[['Username','Rating','Sentiment','Review']]
dfPrompt['Nome'] = dfPrompt['Username'].apply(primeiro_nome)
dfPrompt['prompt'] = dfPrompt.apply(lambda row: createPrompt(row['Sentiment'],row['Rating'], voz, pessoaVerbal, nomeApp, evitar, contato), axis=1)

dfPrompt.loc[dfPrompt['Nome'] != 'Nenhum', 'prompt'] = dfPrompt['prompt']+ '\nUse sempre o nome do cliente: ' + dfPrompt['Nome']

########## API ########## 

API_KEY = st.secrets["TOKEN_API"]
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
url = "https://api.openai.com/v1/chat/completions"
id_modelo = "gpt-3.5-turbo"

if st.button('Gerar Respostas'):
	body_mensagem = {
		"model": id_modelo,
		"messages": [{"role": "user", "content": "Explique, em poucas palavras do que se trata a teoria das cordas"}],
		"max_tokens":10}

	body_mensagem = json.dumps(body_mensagem)

	r = requests.post(url, headers=headers, data=body_mensagem)
	st.write(r)
	st.write(r.reason)

	def gerarResposta(prompt):
		body_mensagem = {
		"model": id_modelo,
		"messages": [{"role": "user", "content": prompt}],
		"max_tokens":2000}
		body_mensagem = json.dumps(body_mensagem)

		r = requests.post(url, headers=headers, data=body_mensagem)
		texto_final = r.json()['choices'][0]['message']['content']

		return texto_final

	for i in range(3):

		dfPrompt[f'Resposta_{i+1}'] = dfPrompt['prompt'].apply(gerarResposta)
	#dfPrompt['respostas'] = dfPrompt['prompt'].apply(gerarResposta)
	dfPrompt.drop(['Nome','prompt'],axis=1, inplace=True)

	st.write(dfPrompt)
	st.write('Clique em Download para baixar o arquivo')
	st.markdown(get_table_download_link(dfPrompt), unsafe_allow_html=True)
