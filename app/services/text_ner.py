import spacy
import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# nlp = spacy.load("en_core_web_sm")


os.environ["TRANSFORMERS_CACHE"] = "./hf_cache"


MODEL_NAME = "dslim/bert-base-NER"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)



# def extract_generalized_entities_from_text(text: str):
#     doc = nlp(text)
#     entities = []
#     for ent in doc.ents:
#         entities.append({
#             "text": ent.text,
#             "label": ent.label_
#         })
    
#     return entities


ner_pipeline = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple",
    device=-1
)

def extract_financial_entities_from_text(text: str):
    ner_results = ner_pipeline(text)
    entities = []
    for ent in ner_results:
        entities.append({
            "text": ent["word"],
            "label": ent["entity_group"]
        })
    return entities