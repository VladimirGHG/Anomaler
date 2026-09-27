class GroupDataStorage:
    def __init__(self):
        self.data = {}

    def add_source_data(self, source_name, data):
        if source_name not in self.data:
            self.data[source_name] = []
        self.data[source_name].extend(data)

    def get_source_data(self, source_name):
        return self.data.get(source_name, [])

    def remove_source_data(self, source_name):
        if source_name in self.data:
            del self.data[source_name]