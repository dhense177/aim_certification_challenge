from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.testset import TestsetGenerator
from ragas.metrics import LLMContextRecall, LLMContextPrecisionWithReference, Faithfulness, ResponseRelevancy
from ragas import evaluate, RunConfig, EvaluationDataset

from agent import app as agent_app
import os
from joblib import load, dump
import ast
import pandas as pd
from agent import rag_node, rag_node_advanced

test_case_file = "testset.joblib"

if os.path.exists(test_case_file):
    dataset = load(test_case_file)
else:
    path = "extracted_data/mass_municipalities/barre/"
    loader = DirectoryLoader(path, glob="*.pdf", loader_cls=PyMuPDFLoader)
    docs = loader.load()

    generator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1"))
    generator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())

    generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings)
    dataset = generator.generate_with_langchain_docs(docs, testset_size=10)
    dump(dataset, test_case_file)

df_dataset = dataset.to_pandas()

########################################################

evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1-mini"))
custom_run_config = RunConfig(timeout=360)

### Baseline Evaluation ###

for test_row in dataset:
    response = rag_node({"query" : test_row.eval_sample.user_input})
    test_row.eval_sample.response = response["result"]
    test_row.eval_sample.retrieved_contexts = [context.page_content for context in response["context"]]

evaluation_dataset = EvaluationDataset.from_pandas(dataset.to_pandas())

baseline_result = evaluate(
    dataset=evaluation_dataset,
    metrics=[LLMContextRecall(), LLMContextPrecisionWithReference(), Faithfulness(),  ResponseRelevancy()],
    llm=evaluator_llm,
    run_config=custom_run_config
)

baseline_result_dict = ast.literal_eval(str(baseline_result))
baseline_result_dict["Retrieval"] = "Baseline"
df_baseline = pd.DataFrame([baseline_result_dict])

### Advanced Evaluation ###

for test_row in dataset:
    response = rag_node_advanced({"query" : test_row.eval_sample.user_input})
    test_row.eval_sample.response = response["result"]
    test_row.eval_sample.retrieved_contexts = [context.page_content for context in response["context"]]


evaluation_dataset_advanced = EvaluationDataset.from_pandas(dataset.to_pandas())

advanced_result = evaluate(
    dataset=evaluation_dataset_advanced,
    metrics=[LLMContextRecall(), LLMContextPrecisionWithReference(), Faithfulness(),  ResponseRelevancy()],
    llm=evaluator_llm,
    run_config=custom_run_config
)

advanced_result_dict = ast.literal_eval(str(advanced_result))
advanced_result_dict["Retrieval"] = "Advanced"
df_advanced = pd.DataFrame([advanced_result_dict])

df_results = pd.concat([df_baseline, df_advanced])
df_results.to_csv("rag_evaluation_results.csv", index=False)