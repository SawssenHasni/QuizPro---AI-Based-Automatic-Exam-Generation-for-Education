import torch
from transformers import BartForConditionalGeneration, BartTokenizer


# Load fine-tuned model and tokenizer
def load_finetuned_model(model_dir):
    tokenizer = BartTokenizer.from_pretrained(model_dir)
    model = BartForConditionalGeneration.from_pretrained(model_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return model, tokenizer, device

# Initialize model (you'll need to set the correct path)
model_dir = "C:/Users/HP/Desktop/Projet Master/Quizpro/APP-Flask1/output_bart-base/model"
model, tokenizer, device = load_finetuned_model(model_dir)

def generate_questions(model, tokenizer, device, paragraph, num_questions, max_length=50,
                      no_repeat_ngram_size=2, early_stopping=True, temperature=0.7, 
                      top_p=0.9, do_sample=True, top_k=50, length_penalty=1.0):
    
    input_text = paragraph + " Question:"
    inputs = tokenizer.encode(input_text, return_tensors='pt').to(device)
    
    outputs = model.generate(
        inputs,
        max_length=inputs.shape[-1] + max_length,
        num_beams=11,
        no_repeat_ngram_size=no_repeat_ngram_size,
        early_stopping=early_stopping,
        num_return_sequences=num_questions,
        temperature=temperature,
        top_p=top_p,
        do_sample=do_sample,
        top_k=top_k,
        length_penalty=length_penalty)
    
    generated_questions = []
    for output in outputs:
        question = tokenizer.decode(output, skip_special_tokens=True).replace(paragraph, "").replace("Question:", "").strip()
        generated_questions.append(question)
    return generated_questions