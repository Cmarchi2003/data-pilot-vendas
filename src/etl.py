import pandas as pd

df = pd.read_csv('data/raw/sales.csv')

print(df.head())
print(df.dtypes)
print(df.shape)

df['data'] = pd.to_datetime(df['data'], errors='coerce')
df['mes'] = df['data'].dt.to_period('M').astype(str)
df['status'] = df['status'].str.strip().str.lower()
df = df.drop_duplicates()

df['receitas'] = df['quantidade'] * df['preco_unitario']

#salvar os dados processados em um novo arquivo CSV

df.to_csv('data/processed/sales_processed.csv', index=False, sep=';', decimal=',')
print("Dados processados e salvos em 'data/processed/sales_processed.csv'")

df_clean = pd.read_csv('data/processed/sales_processed.csv', sep=';', decimal=',')
print(df_clean.head())