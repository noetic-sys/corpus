YOU WILL FOLLOW THESE RULES: 

- api paths go in api/v1/. if there is a file where it makes sense, you may add it to this file. if not add a new endpoints file
- data accessing logic all goes in repositories/
- models go in models/ - database models in models/database and models to pass around services go in models/domain. never use entity models at the service layer
- providers holds things where we want a common interface but maybe multiple implementations / providers - ie messaging queue brokers, ai providers, etc. 
- services go in services/ where this holds business / service logic
- schemas/ holds api level schema types