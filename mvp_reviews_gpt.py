#### MVP - PULSE GPT
import streamlit as st
import pandas as pd
import numpy as np
import xlsxwriter
import requests
import json
import base64
from io import BytesIO
import time
import asyncio
import aiohttp
import altair

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

st.title("PulseGPT")
st.write('Esta aplicação tem como objetivo auxiliar o time de atendimento de Pulse Solution com respostas geradas por IA')
st.write()

# Inserindo Review Sheet
reviewSheet = st.file_uploader("Insira um arquivo .xlsx da Review Sheet")
if reviewSheet is not None:
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
		if nome == 'Um usuário do Google':
			return 'Nenhum'
		elif len(nome_split) > 1:
			return nome_split[0]
		else:
			return 'Nenhum'

	def createPrompt(sentiment, rating, review, voz, pessoaVerbal, nomeApp, evitar, contato):
		infos = f'''Responda no seguinte tom de voz: {voz} na {pessoaVerbal}  
		\nNome do aplicativo: {nomeApp}
		\nEvite nas respostas: {evitar}
		\nQuando julgar necessário, insira o Contato: {contato}'''

		prompt = f"""Haja como um atendente de um aplicativo que responde os comentários dos usuários.
		Cada resposta deve ter NO MÁXIMO 270 caracteres e seguir às seguintes instruções: 
		Sempre inicie a resposta com uma saudação ao cliente. 
		Separe a saudação do nome por vírgula.
		Comentário de sentimento positivo, responda agradecendo ao usuário e 
		Para sentimento negativo, responda se desculpando. 
		Para Rating de 1 a 5, considere 1 como "Muito Insatisfeito" e 5 como "Muito Satisfeito".
		Sempre use a expressão 'app' ou 'aplicativo' antes de se referir ao nome do aplicativo. 
		\n{infos} 
		\nSentimento: {sentiment}
		\nRating: {rating}
		\nMáximo de caracteres na resposta: 250
		\nComentário: {review}"""

		return prompt


	dfPrompt = df[['Username','Rating','Sentiment','Review']]
	dfPrompt['Nome'] = dfPrompt['Username'].apply(primeiro_nome)
	dfPrompt['prompt'] = dfPrompt.apply(lambda row: createPrompt(row['Sentiment'],row['Rating'],row['Review'], voz, pessoaVerbal, nomeApp, evitar, contato), axis=1)

	dfPrompt.loc[dfPrompt['Nome'] != 'Nenhum', 'prompt'] = dfPrompt['prompt']+ '\nUse sempre o nome do cliente: ' + dfPrompt['Nome']

	########## API ########## 

	if st.button('Gerar Respostas'):

		prompts = list(dfPrompt['prompt'])

		API_KEY = st.secrets["TOKEN_API"]

		headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
		url = "/v1/chat/completions"
		url_base = "https://api.openai.com"
		id_modelo = "gpt-3.5-turbo"

		async def getData(session, body_mensagem):
			response = await session.post(url, headers=headers, data=body_mensagem)
			body = await response.json()
			response.close()
			return body

		async def getChatgptResponses(prompts):
			session = aiohttp.ClientSession(url_base)
			tasks = []
			for prompt in prompts:
		        
				body_mensagem = {
				"model": id_modelo,
				"messages": [{"role": "user", "content": prompt}],
				"max_tokens":300}

				body_mensagem = json.dumps(body_mensagem)
				tasks.append(getData(session,body_mensagem))
				tasks.append(getData(session,body_mensagem))
				tasks.append(getData(session,body_mensagem))
			data = await asyncio.gather(*tasks)
			await session.close()
			return data

		results = asyncio.run(getChatgptResponses(prompts))

		dfResults = pd.DataFrame(results)
		dfNorm = pd.json_normalize(pd.DataFrame(dfResults.explode('choices')['choices'])['choices'])
		st.write(dfNorm)
		#listReplies =  list(dfNorm['message.content'])

		# Divide a lista em pedaços de três itens e atribui a cada coluna
		#dfPrompt['Resposta_1'] = replies[::3]
		#dfPrompt['Resposta_2'] = replies[1::3]
		#dfPrompt['Resposta_3'] = replies[2::3]

		#dfPrompt.drop(['Nome','prompt'],axis=1, inplace=True)
		
		#st.write(dfPrompt)
		#st.write('Clique em Download para baixar o arquivo')
		#st.markdown(get_table_download_link(dfPrompt), unsafe_allow_html=True)
