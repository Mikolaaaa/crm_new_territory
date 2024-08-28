from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import re
import logging

logging.basicConfig(level=logging.INFO, filename="ml_log.log",filemode="a", encoding='utf-8')

app = FastAPI()

class request_body(BaseModel):
	question : str
	id: int
	id_category: int
      
class request_body_k_top(BaseModel):
	indexs: list[int]

class request_body_k_top_category(BaseModel):
	indexs: list[dict]

model_encoder = SentenceTransformer('ai-forever/rugpt3small_based_on_gpt2', cache_folder='models/') # новая моделька?
data_questions = pd.read_csv('data/data_questions.csv') # векторная база нужна
COLUMNS_DROP = ['question', 'id', 'id_category']

def find_inn(x, len):
	find = re.search(r'\D\d{' + str(len) + '}\D', x)
	if find != None:
		return find.group(0)
	return None

def mask_inn(x):

	inn_12 = find_inn(x, 12)
	while inn_12 != None:  
		x = x.replace(inn_12, ' IT_INN_12 ')
		inn_12 = find_inn(x, 12)

	inn_10 = find_inn(x, 10)
	while inn_10 != None:  
		x = x.replace(inn_10, ' IT_INN_10 ')
		inn_10 = find_inn(x, 10)

	return x

@app.post('/encode-record')
def encode_record(data : request_body):
     
	global data_questions
     
	if data_questions[data_questions['id']==data.id].shape[0] > 0:
		return {'respone': 'Данные уже есть в базе'}

	input_data = mask_inn(data.question)
	data_encode = model_encoder.encode(input_data)
	data_add = [data.question, data.id, data.id_category, 1] + list(data_encode)
    
	data_questions = pd.concat([data_questions, data_add])

	return {'respone': 'Данные приняты!'}

@app.post('/k-top-questions')
def get_k_top_questions(data : request_body_k_top):
     
	global data_questions
     
	indexs = {}
	for index in data.indexs:
		list_index = []
		if data_questions[data_questions['id']==index].shape[0] != 0:
			data_encode = data_questions[data_questions['id']==index].drop(columns=COLUMNS_DROP).to_numpy()
			full_data_encode = data_questions[data_questions['not_answer']==0].drop(columns=COLUMNS_DROP).to_numpy()
			top_k = util.semantic_search(data_encode, full_data_encode, top_k=6)
			for i in top_k[0]: # закомментить для проверки
				if i['score'] >= 0.99999:
					continue
				if i['score'] < 0.95:
					break
				list_index.append(int(data_questions.loc[i['corpus_id'], 'id']))
		indexs[index] = list_index

	return {'indexs': indexs}

@app.post('/k-top-category')
def get_k_top_category(data : request_body_k_top_category):
     
	global data_questions
     
	indexs = {}
	for index in data.indexs:
		list_index = []
		if data_questions[data_questions['id']==index['id']].shape[0] != 0:
			data_encode = data_questions[data_questions['id']==index['id']].drop(columns=COLUMNS_DROP).to_numpy()
			full_data_encode = data_questions[data_questions['not_answer']==0].drop(columns=COLUMNS_DROP).to_numpy()
			top_k = util.semantic_search(data_encode, full_data_encode, top_k=6)

			for i in top_k[0]:
				if i['score'] >= 0.99999:
					continue
				if i['score'] < 0.95:
					break
				id_category = int(data_questions.loc[i['corpus_id'], 'id_category'])
				if id_category != index['category_id']:
					list_index.append(id_category)
		indexs[index['id']] = list(set(list_index))

	return {'indexs': indexs}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)