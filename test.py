from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights
# res = tavily_search("Best Hotels in Toronto")
# print(res)
res = search_flights("Plan a 7 days Iran trip from Toronto")
print(res)