# class DatabaseConnection:
#     _instance = None

#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super(DatabaseConnection, cls).__new__(cls)
#             cls._instance.connected = False
#         return cls._instance

#     def connect(self):
#         if not self.connected:
#             self.connected = True
#             print("Connected to database")

#     def disconnect(self):
#         self.connected = False
#         print("Disconnected")

# # Test
# db1 = DatabaseConnection()
# db2 = DatabaseConnection()

# db1.connect()
# print(db1 is db2)  # True