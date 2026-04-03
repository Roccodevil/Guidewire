import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

class DispatchDecision(BaseModel):
    selected_worker_id: int = Field(description="The ID of the best matched worker")
    xai_reasoning: str = Field(description="Business reasoning explaining why this minimizes platform liability and protects worker earnings.")
def auto_assign_order(order_details: dict, available_workers: list) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"selected_worker_id": available_workers[0]['id'], "xai_reasoning": "Fallback to first worker."}

    parser = JsonOutputParser(pydantic_object=DispatchDecision)
    llm = ChatGroq(temperature=0.1, model_name="llama-3.1-8b-instant", groq_api_key=api_key)

    prompt = PromptTemplate(
        template="""
        You are the Operations Manager for a high-volume delivery fleet.
        An order has come in for a zone with: {order_details}
        
        Available Fleet: {workers}
        
        BUSINESS OBJECTIVE:
        Minimize unmitigated risk exposure. If the route is high-risk, assigning an uninsured worker guarantees they suffer 100% income loss if gridlocked, resulting in platform churn. Assigning an insured worker transfers that financial risk to our parametric pool.
        
        Select the optimal worker ID and provide a 1-sentence 'xai_reasoning' justifying the operational liability mitigation.
        
        {format_instructions}
        """,
        input_variables=["order_details", "workers"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser

    try:
        return chain.invoke({"order_details": order_details, "workers": available_workers})
    except Exception as e:
        print(f"Dispatch AI Error: {e}")
        return {"selected_worker_id": available_workers[0]['id'], "xai_reasoning": "Fallback routing used due to AI timeout."}