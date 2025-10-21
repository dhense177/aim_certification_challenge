from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
# from langchain.schema import RunnableConfig
from typing import TypedDict, Literal, Optional
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from tool_utils import geocode_address
from tool_utils import get_solar_resource
from rag_utils import get_qa_chain, get_qa_chain_advanced
from typing_extensions import List
from langchain_core.documents import Document
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "solar-certification-assistant"

qa_chain = get_qa_chain()
qa_chain_advanced = get_qa_chain_advanced()

# Define Pydantic model for coordinate extraction
class Coordinates(BaseModel):
    latitude: float = Field(..., description="The latitude coordinate as a decimal number")
    longitude: float = Field(..., description="The longitude coordinate as a decimal number")

# Define shared state
class AgentState(TypedDict):
    query: str
    route: Optional[Literal["municipality", "site"]]
    result: Optional[str]
    context: Optional[List[Document]]


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
router_prompt = PromptTemplate.from_template("""
Decide if this question is about:
- a specific site/address - must have address text in the question (output "site"),
- anything else (output "municipality"),

Question: {question}
Answer:
""")
router_chain = router_prompt | llm | StrOutputParser()

def route_question(state: AgentState) -> AgentState:
    route = router_chain.invoke({"question": state["query"]}).strip().lower()
    return {**state, "route": route}

def site_tool_node(state: AgentState) -> AgentState:
    query = state["query"]
    
    # Use LLM to extract address from user query
    address_extraction_prompt = PromptTemplate.from_template("""
        Extract the complete address from the following user query. Return ONLY the address in a standard format.

        User query: {query}

        Return the address in the format: "Street Number Street Name, City, State ZIP Code, Country"
        If no address is found, return "ERROR".
    """)
    
    try:
        # Extract address using LLM
        address_chain = address_extraction_prompt | llm | StrOutputParser()
        extracted_address = address_chain.invoke({"query": query})
        
        if "ERROR" in extracted_address:
            answer = f"Could not extract address from query: {query}"
        else:
            # Geocode the extracted address
            geocode_result = geocode_address.invoke({"address": extracted_address})
            
            if "No result found" in geocode_result:
                answer = f"Could not find coordinates for address: {extracted_address}\nGeocode result: {geocode_result}"
            else:
                # Extract lat/lon from geocode result using simple parsing
                try:
                    lines = geocode_result.split(", ")
                    lat_line = [line for line in lines if line.startswith("Latitude:")][0]
                    lon_line = [line for line in lines if line.startswith("Longitude:")][0]
                    
                    lat = lat_line.split("Latitude: ")[1]
                    lon = lon_line.split("Longitude: ")[1]
                    lat_lon = f"{lat},{lon}"
                    
                    # Get solar resource data
                    solar_result = get_solar_resource.invoke({"lat_lon": lat_lon})
                    
                    answer = f"Extracted Address: {extracted_address}\n{geocode_result}\n\nSolar Resource Data:\n{solar_result}"
                except Exception as parse_error:
                    answer = f"Error parsing coordinates: {str(parse_error)}\nGeocode result: {geocode_result}"
    except Exception as e:
        answer = f"Error processing query: {str(e)}"
    
    return {**state, "result": answer}

def rag_node(state: AgentState) -> AgentState:
    query = state["query"]
    result = qa_chain.invoke({'question': query})
    
    return {**state, "result": result['response'].content, "context": result['context']}


def rag_node_advanced(state: AgentState) -> AgentState:
    query = state["query"]
    result = qa_chain_advanced.invoke({'question': query})
    return {**state, "result": result['response'].content, "context": result['context']}

graph = StateGraph(AgentState)

graph.add_node("route_question", route_question)
graph.add_node("rag", rag_node_advanced)
graph.add_node("tool", site_tool_node)

graph.set_entry_point("route_question")
graph.add_conditional_edges("route_question", lambda state: state["route"], {
    "municipality": "rag",
    "site": "tool"
})

graph.add_edge("rag", END)
graph.add_edge("tool", END)

app = graph.compile()


# Examples
# result = app.invoke({"query": "Evaluate solar potential at 47 Newton St, Barre, MA 01005 United States"})
# print(result["result"])

# result = app.invoke({"query": "In Boston, MA, what are the zoning regulations for solar development?"})
# print(result["result"])

# result = app.invoke({"query": "What’s the weather like?"})
# print(result["result"])