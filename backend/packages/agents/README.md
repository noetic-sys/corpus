package for working with multi step agents and conversations

users should be able to have multi-step conversations with agents (ie, agents can take multiple calling turns like in claude code / gemini), 
and do semi-autonomous work, as well as analysis tasks for the user like analyzing matrices, reading documents, etc. 

general layout 

models - domain, database, schemas. each for a separate level. domain for domain level models to be passed around by services, database for entity definitoins on sqlite, and schemas for api level
repositories - use @common/repositories/base.py to define repositories for interacting with the database elements and returning domain level objefts
routes - api routes. i expect to be able to start conversations, and partake in them from user perspective. we likely need regular rest routes as well as websockets for the actual chatting of messages between frontend and backend. 
services - actual services to take care of work - ie create conversations, list emssages in order,add new messages, execute tools, etc. 
tools - tool registry for the agents / models
tools/tools - actual tools (example one provided)
