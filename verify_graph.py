from langchain_openai import ChatOpenAI
from generate_synthetic_table.flow import build_synthetic_table_graph

def verify_graph():
    llm = ChatOpenAI(api_key="test")
    
    # Test OpenAI provider (Direct path)
    graph_openai = build_synthetic_table_graph(llm, provider="openai")
    print("OpenAI Graph Nodes:", graph_openai.nodes.keys())
    app_openai = graph_openai.compile()
    print("OpenAI Graph compiled successfully.")

    # Test vLLM provider (Multi-stage path)
    graph_vllm = build_synthetic_table_graph(llm, provider="vllm")
    print("vLLM Graph Nodes:", graph_vllm.nodes.keys())
    app_vllm = graph_vllm.compile()
    print("vLLM Graph compiled successfully.")

if __name__ == "__main__":
    verify_graph()
