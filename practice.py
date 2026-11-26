from typing import TypedDict
from langgraph.graph import StateGraph , START , END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt , Command


class Test_result(TypedDict):
    test_result :str 
    bug_creation : bool
    
def test_result(state:Test_result):
    print("Test cases are failed")
    return {state["test_result"]:"FALSE"}
def approve_ticket(state:Test_result):
    approve = interrupt("test cases failed , do you want me to create jira ticket?")
    if approve:
        print("jirs ticket created successfully")
        return{state["bug_creation"]:True}
    return{state["bug_creation"]:False}
def create_ticket(state:Test_result):
    if state["bug_creation"] == True:
        print("ticket created successfully ")
    else : 
        print("Ticket creation rejected ")
    return {}

check_pointer = InMemorySaver()
config = {
    "configurabel":
        {"thread_id":"TC_001"}
}

graph = StateGraph(Test_result)
graph.add_node("test_result",test_result)
graph.add_node("approve_ticket",approve_ticket)
graph.add_node("create_ticket",create_ticket)
graph.add_edge(START ,"test_result")
graph.add_edge("test_result","approve_ticket")
graph.add_edge("approve_ticket","create_ticket")
graph.add_edge("create_ticket",END)

app = graph.compile(checkpointer=check_pointer)

result = app.invoke({"test_result":"Pass","bug_creation":""},config=config)

print(result)
result = app.invoke(Command(resume=True),config=config)
print(result)
