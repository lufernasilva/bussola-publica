-- Fase 0: Estrutura base já aplicada no Supabase
CREATE TABLE IF NOT EXISTS dim_partidos (
    id_partido INTEGER PRIMARY KEY,
    sigla VARCHAR(20) NOT NULL UNIQUE,
    nome VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_deputados (
    id_deputado INTEGER PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    sigla_partido VARCHAR(20),
    sigla_uf CHAR(2),
    url_foto TEXT
);

CREATE TABLE IF NOT EXISTS fato_proposicoes (
    id_proposicao INTEGER PRIMARY KEY,
    sigla_tipo VARCHAR(20) NOT NULL,
    numero INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    ementa TEXT NOT NULL,
    data_apresentacao TIMESTAMP,
    status_tramitacao TEXT,
    id_deputado_autor INTEGER REFERENCES dim_deputados(id_deputado),
    criado_em TIMESTAMP DEFAULT NOW()
);
