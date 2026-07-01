# TODO

## Remplacer l'inference de forme/type de `compile_graph` par Spox

`compile_graph` (server.py) est composee de deux moities : (A) un moteur "description d'ops -> ONNX avec inference forme/type" (les `_output_shape_for_*` + propagation de types dans `same_shape_ops`, `tensor_shape`, `tensor_type`), et (B) le reste (assemblage nodes/initializers, gate de validation ARC-specifique). La moitie (A) est exactement le code qui grossit a chaque nouvel op (cf. `COMPILER_TODOS.md`), et c'est celle qui a un equivalent open-source mur.

### Candidats open-source

- **Spox** -- https://github.com/Quantco/spox (docs : https://spox.readthedocs.io/). Candidat n°1. On manipule des `Var` (placeholders) et Spox fait tourner l'inference forme/type ONNX a la volee pendant l'assemblage : il attrape les mismatches _avant_ le `ModelProto`. C'est precisement notre boucle `same_shape_ops` + `tensor_shape`/`tensor_type`, mais automatisee pour tout l'opset standard. Si l'objectif est de supprimer l'inference manuelle, c'est le bon levier.
- **ONNX Script** -- https://github.com/microsoft/onnxscript. Ecrire des ONNX functions en syntaxe Python-like, compilees en ONNX (backend du nouvel exporteur `torch.onnx` dynamo). Plus oriente "ecrire du ONNX comme du code" que "assembler un graphe depuis des donnees", donc moins direct pour notre cas JSON -> graphe.
- Plus bas niveau (ne font PAS l'inference de forme, donc n'epargnent pas le gros du travail) : **sclblonnx** (helpers d'assemblage), **onnx-graphsurgeon** (edition de graphes existants), **onnx.shape_inference** (builtin `onnx`, deja installe -- mais change la semantique d'erreur : les mismatches remonteraient a l'inference finale, plus au build inline).

### Editeur visuel (partie B, front) -- pour reference, pas a remplacer

Notre canvas React Flow est deja mieux integre a notre workflow que ces alternatives : **onnx-modifier** (https://github.com/ZhangGe6/onnx-modifier, Netron + Flask), **ONNX Script Visual Editor** (https://josephrocca.github.io/onnxscript-editor/demo/), **OnnxEditorV2** (https://github.com/OYCN/OnnxEditorV2, Qt desktop).

### Verdict

Aucun projet ne remplace `compile_graph` en bloc : la partie ARC-specifique (shape statique `[1,1,30,30]` = `CANVAS_SHAPE`, slots d'entree nommes via `INPUT_SLOT_ORDER`, gate de validation 3 phases) est propre au depot. Le refactor a valeur est cible : reecrire (A) sur Spox pour que `compile_graph` devienne une couche mince "JSON -> appels d'ops Spox", Spox gerant shapes/types/erreurs.

### Prochaine etape

Prototyper `compile_graph` sur Spox pour 2-3 ops representatifs (Slice / Where / Conv) et mesurer combien de lignes d'inference forme/type sont eliminees avant de decider du refactor complet.
