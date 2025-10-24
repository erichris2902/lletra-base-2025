class ToolDomain:
    VALID_TYPES = ("function", "retrieval", "code_interpreter")

    def __init__(self, name, type_, description="", parameters=None):
        if type_ not in self.VALID_TYPES:
            raise ValueError(f"Tipo de tool inválido: {type_}")
        self.name = name
        self.type = type_
        self.description = description
        self.parameters = parameters or {}

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "parameters": self.parameters,
        }

    def summary(self):
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description[:50] + "..." if len(self.description) > 50 else self.description
        }
