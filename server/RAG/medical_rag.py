import os
import time
from math import exp
import numpy as np
from IPython.display import display, HTML

import hashlib

from dotenv import load_dotenv
import openai
from openai import OpenAI
import json  # pyright: ignore[reportUnusedImport]
from pinecone import Pinecone
import time

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

import re
import textwrap
import fitz

delimiter = "########"
chatContext = [
    {'role':'system', 'content': f"""\
You are an advanced and amiable virtual assistant, specifically designed to assist with queries related to medical knowledge, services \
and doctor schedule provided by El Camino Health.

As the designated virtual assistant for this class, your role is to provide accurate and helpful responses based on the medical document. \
Your responses should adhere to the information contained within the specified context, marked by {delimiter}.

Your primary goal is to support and enhance the experience of patients seeking for medical information, services and doctor schedule provided by El Camino Health.
"""
}
]

limit = 8000
NUM_KNOWLEDGE_TXT = 68

def get_completion(
    messages: list[dict[str, str]],
    model: str = "gpt-4o-mini",
    max_tokens=500,
    temperature=0,
    stop=None,
    seed=123,
    tools=None,
    logprobs=None,  # whether to return log probabilities of the output tokens or not. If true, returns the log probabilities of each output token returned in the content of message.
    top_logprobs=None,
) -> str:
    params = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stop": stop,
        "seed": seed,
        "logprobs": logprobs,
        "top_logprobs": top_logprobs,
    }
    if tools:
        params["tools"] = tools

    completion = client.chat.completions.create(**params)
    return completion

def cosine_similarity_vectors(vector1, vector2):
    # Calculate the cosine similarity between the vectors
    similarity = cosine_similarity([vector1], [vector2])
    return similarity[0][0]

def extract_clean_120_list(pdf_path: str) -> list[str]:
    """Return cleaned PDF text as a list of lines (wrapped at 120 chars)."""
    import re, textwrap, fitz

    doc = fitz.open(pdf_path)
    raw = "\n".join(p.get_text() for p in doc)

    # Fix hyphenations and unwrap soft breaks
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', raw)
    text = re.sub(r'(?<![.!?;:])\n(?!\n)', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Split into paragraphs, wrap to 120 chars
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    wrapped_paras = [
        textwrap.fill(p, width=120, break_long_words=False, break_on_hyphens=False)
        for p in paras
    ]

    # Finally, flatten paragraphs into list of lines
    lines = []
    for para in wrapped_paras:
        lines.extend(para.splitlines())
        lines.append("")  # keep blank line between paragraphs
    if lines and lines[-1] == "":
        lines.pop()  # remove trailing blank line

    return lines


def wrap_text(text, max_line_length=100):
    """
    Wrap text to maximum line length
    """
    if len(text) <= max_line_length:
        return text
    lines = text.split('\n')
    wrapped_lines = [textwrap.fill(line, width=max_line_length) for line in lines]
    return '\n'.join(wrapped_lines)

class RAG:
  def __init__(self):
    global delimiter, chatContext
    self.build_RAG()
    delimiter = "########"
    chatContext = [
      {'role':'system', 'content': f"""\
You are an advanced and amiable virtual assistant, specifically designed to assist with queries related to medical knowledge, services \
and doctor schedule provided by El Camino Health.

As the designated virtual assistant for this class, your role is to provide accurate and helpful responses based on the medical document. \
Your responses should adhere to the information contained within the specified context, marked by {delimiter}.

Your primary goal is to support and enhance the experience of patients seeking for medical information, services and doctor schedule provided by El Camino Health.
"""
      }
    ]
    self.chatBot_Response = ''
    self.set_rag_env()
    
  def get_chatBot_Response(self):
    return self.chatBot_Response
    
  def response_request(
    self,
    messages,
    model,
    tools=None,
    tool_choice="auto",
    conversation=None,
    max_output_tokens=None,
    temperature=None,   # will be ignored for gpt-5 models
  ):
    if str(model).startswith("gpt-5"):
      # Do NOT send temperature for gpt-5 family
      return self.client.responses.create(
        model=model,
        input=messages,
        tools=tools,
        tool_choice=tool_choice,
        conversation=conversation,
        max_output_tokens=max_output_tokens,
        )
    else:
      # Non–gpt-5 models can receive temperature
      return self.client.responses.create(
        model=model,
        input=messages,
        tools=tools,
        tool_choice=tool_choice,
        conversation=conversation,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        )
    
  def build_RAG(self):
    global NUM_KNOWLEDGE_TXT
    load_dotenv()
    # Assign pinecone PINECONE_API_KEY
    pinecone_api_key = os.getenv("PINECONE_API_KEY")

    self.client = OpenAI()
    self.pc = Pinecone(api_key=pinecone_api_key)
    
    self.MODEL = "gpt-4o-mini"
    
    self.embed_model = "text-embedding-3-small"

    self.res = self.client.embeddings.create(
      input=[
        "I need to visit the bank to deposit some cash.",

        "I have to stop by the financial institution to save money to my account.",

        "One of my favorite pastimes is leisurely swimming along the meandering river bank."
      ],
      model=self.embed_model
      )

    self.index_name = "felixpinecone"
    # exists-or-create
    if self.index_name not in self.pc.list_indexes().names():  # .names() is correct in the   new client
      self.pc.create_index(
        name=self.index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        deletion_protection="disabled",
        tags={"environment": "development"},
        vector_type="dense",
      )

    # wait until ready
    while not self.pc.describe_index(self.index_name).status["ready"]:
      pass
    print("Index ready.")
  
    # connect to index
    self.index = self.pc.Index(self.index_name)
    # view index stats
    self.index.describe_index_stats()
  
    # Get the directory where this file is located
    import pathlib
    rag_dir = pathlib.Path(__file__).parent.resolve()
    
    fn = str(rag_dir / "services_Stanford_Hospital_offer.txt")
    self.nlp_upsert(fn, self.index_name, "sjsunlp","nlp", 9, 3)
  
    for k in range(1, NUM_KNOWLEDGE_TXT + 1):
      fn_txt = str(rag_dir / f'tmp{k}.txt')
      nlp_id = 'nlp' + str(k)
      self.nlp_upsert(fn_txt, self.index_name, "sjsunlp", nlp_id, 9, 3)
      print(fn_txt)
  
    self.limit = 8000  #set the limit of knowledge base words, leave some space for chat history and query.
    
  def set_rag_env(self):
    global retrieved_knowledge, knowledge_message, context_query_knowledge, response, response_message, chatContext, chatBotResponse
    
    query = 'I have occasional heart ache and blood flow issues. Can you find a doctor for me? '
    query_message = {"role": "user", "content": f"""
      {query}
      """
    }
    print("query:", query)
    print("query message:", query_message)
    chatContext.append(query_message)
    res = self.client.embeddings.create(
      input=[query],
      model=self.embed_model
    )

    # retrieve from Pinecone
    xq = res.data[0].embedding

    # get relevant contexts
    res = self.index.query(vector=xq,
                  top_k=3,
                  include_metadata=True,
                  namespace='sjsunlp')
    print(f"res: {res}")
    self.contexts = [
        x["metadata"]["text"] for x in res["matches"]
    ]
    
    retrieved_knowledge = self.retrieve(query,"sjsunlp")
    print(retrieved_knowledge)
    
    # Infuse the knowledge into the final messages
    knowledge_message = {"role": "system", "content": f"""
    {retrieved_knowledge}
    """
    }
    
    context_query_knowledge = chatContext + [knowledge_message, query_message]
    print("context_query_knowledge: ", context_query_knowledge)
    
    response = self.response_request(context_query_knowledge, model=self.MODEL, temperature=0)
    
    self.chatBot_Response = wrap_text(response.output_text)
    # print(self.chatBot_Response)

    response_message = {"role": "assistant", "content":f"{response.output_text}"}
    chatContext.append(response_message)
  
  def query_RAG(self, query):
    global retrieved_knowledge, knowledge_message, context_query_knowledge, response, response_message, chatContext, chatBotResponse
    query = query + " "

    query_message = {"role": "user", "content": f"""
    {query}
    """
    }
    print("\nquery:", query)
    # print("query message:", query_message)
    chatContext.append(query_message)

    res = self.client.embeddings.create(
      input=[query],
      model=self.embed_model
    )

    # retrieve from Pinecone
    xq = res.data[0].embedding

    # get relevant contexts
    res = self.index.query(vector=xq,
                    top_k=3,
                    include_metadata=True,
                    namespace='sjsunlp')
    # print(res)

    self.contexts = [
        x["metadata"]["text"] for x in res["matches"]
    ]

    # print(contexts)

    # first we retrieve relevant items from Pinecone
    retrieved_knowledge = self.retrieve(query,"sjsunlp")

    # print(retrieved_knowledge)

    # Infuse the knowledge into the final messages
    knowledge_message = {"role": "system", "content": f"""
    {retrieved_knowledge}
    """
    }

    # Come out a temp list to hold knowledge
    context_query_knowledge = chatContext + [knowledge_message, query_message]
    # print("context_query_knowledge: ", context_query_knowledge)

    response = self.response_request(context_query_knowledge, model=self.MODEL, temperature=0)

    # print(response.output_text)
    chatContext.append(response_message)
    self.chatBot_Response = wrap_text(response.output_text)
    # print(self.chatBot_Response)
    
    response_message = {"role": "assistant", "content":f"{response.output_text}"}
    chatContext.append(response_message)
    return self.chatBot_Response

  def retrieve(self, query, name_space):
    global limit, delimiter
    res = self.client.embeddings.create(
        input=[query],
        model=self.embed_model
    )

    # retrieve from Pinecone knowledge base
    xq = res.data[0].embedding

    # get relevant contexts
    res = self.index.query(vector=xq,
                      top_k=3,
                      include_metadata=True,
                      namespace=name_space)
    self.contexts = [
        x["metadata"]["text"] for x in res["matches"]
        ]

    #print("Length of contexts: ", len(contexts))
    #print(contexts)

    # build our prompt with the retrieved contexts included
    prompt = " "

    # append contexts until hitting limit
    count = 0
    proceed = True
    while proceed and count < len(self.contexts):
        if len(prompt) + len(self.contexts[count]) >= limit:
            proceed = False
        else:
            prompt += self.contexts[count]

        count += 1
    # End of while loop

    prompt = delimiter + prompt + delimiter

    return prompt

  def nlp_upsert(self, filename, index_name, name_space, nlp_id, chunk_size, stride):
    """
    upsert a whole PDF file (with begin page and end page information) to the pinecone vector database

    Parameters:
    filename (str): The file name.
    index_name (str): The pinecone index name.
    name_space (str): The namespace we want to place for all related docuement.
    nlp_id (str): A common ID prefix to reference to document.
    chunk_size (int): The chunk size, how many lines as one chunks.
    stride (int): The overlap side, how many lines as overlap between chunks.

    Returns:
    None: No return.
    """
    print("extracting pdf...")
    doc = extract_clean_120_list(filename)
    print("extracting finished! Total Lines: ", len(doc))

    count = 0
    for i in range(0, len(doc), chunk_size):
      #find begining and end of the chunk
      i_begin = max(0, i-stride)
      i_end = min(len(doc), i_begin+chunk_size)

      doc_chunk = doc[i_begin:i_end]
      print("-"*80)
      print("The ", i//chunk_size + 1, " doc chunk text:", doc_chunk)


      texts = ""
      for x in doc_chunk:
        texts += x
      print("Texts:", texts)

      #Create embeddings of the chunk texts
      try:
        res = self.client.embeddings.create(input=texts, model=self.embed_model)
      except:
        done = False
        while not done:
          time.sleep(10)
          try:
            res = self.client.embeddings.create(input=texts, model=self.embed_model)
            done = True
          except:
            pass
      embed = res.data[0].embedding
      print("Embeds length:", len(embed))

      # Meta data preparation
      metadata = {
        "text": texts
      }

      count += 1
      print("Upserted vector count is: ", count)
      print("="*80)

      #upsert to pinecone and corresponding namespace

      self.index.upsert(vectors=[{"id": nlp_id + '_' + str(count), "metadata": metadata, "values": embed}], namespace=name_space)
