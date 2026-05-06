# Alcance del Proyecto

## Definicion oficial

Nodos Funcionales es una plataforma bioinformatica multiorganismo para la priorizacion explicable de blancos terapeuticos bacterianos. El sistema permite que el usuario ingrese informacion genomica, funcional, clinica o curada de cualquier organismo bacteriano, y combina esta evidencia con fuentes externas, catalogos, redes funcionales y modelos de puntuacion multicapa para identificar candidatos terapeuticos con potencial antibacteriano, antivirulencia, sensibilizador o de nodo funcional. La plataforma incorpora auditoria de procedencia, evaluacion de confiabilidad, clasificacion del rol terapeutico y estimacion progresiva del riesgo evolutivo de escape, permitiendo generar rankings interpretables y comparables entre organismos.

## Objetivo general

Desarrollar una plataforma bioinformatica multiorganismo para la priorizacion explicable de blancos terapeuticos bacterianos, capaz de integrar datos proporcionados por el usuario y fuentes externas curadas o automatizadas, con el fin de identificar genes, proteinas o nodos funcionales con potencial como blancos antibacterianos, antivirulencia, sensibilizadores terapeuticos o nodos funcionales estrategicos.

## Objetivos especificos

- Disenar una arquitectura modular que permita cargar datos de diferentes organismos bacterianos mediante workspaces independientes.
- Integrar capas de evidencia biologica y terapeutica, incluyendo esencialidad, virulencia, conservacion entre cepas, homologia con el hospedero, localizacion subcelular, redes funcionales, impacto clinico, contexto de enfermedad y sitio de infeccion.
- Implementar un sistema de puntuacion multicapa que permita clasificar candidatos como blancos antibacterianos clasicos, blancos antivirulencia, nodos funcionales, sensibilizadores o candidatos de baja prioridad.
- Incorporar mecanismos de auditoria que indiquen el origen, fortaleza, procedencia y confiabilidad de cada capa de evidencia usada en la priorizacion.
- Permitir la comparacion entre escenarios con datos reales, datos curados, fuentes externas, cache, datos demo y proveedores controlados.
- Desarrollar reportes interpretables que indiquen por que un candidato fue priorizado, que evidencia lo respalda y que informacion falta.
- Incorporar progresivamente una dimension evolutiva que estime riesgo de escape adaptativo, probabilidad de resistencia, redundancia funcional y reduccion del espacio evolutivo al dirigir la terapia contra nodos funcionales.

## Referencias a organismos concretos

Las referencias a `Pseudomonas aeruginosa` PAO1, `Corynebacterium pseudotuberculosis`, `Mycobacterium tuberculosis` H37Rv y `Helicobacter pylori` son ejemplos, demos, entradas de cache taxonomico o casos de validacion. No definen el alcance biologico exclusivo del proyecto.

## Lo que no implica el alcance actual

- No valida eficacia terapeutica por si solo.
- No sustituye curacion bibliografica ni validacion experimental.
- No exige un organismo especifico.
- No exige que todas las capas esten completas para ejecutar un analisis preliminar, pero siempre debe auditar faltantes, proxies y procedencia.
