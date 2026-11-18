"""Portuguese prompts for a still or an animated sticker."""

_KIND = (
    "Diga que tipo de imagem é: foto, figurinha, meme, captura de tela ou desenho. "
    "Diga o assunto principal. "
    "Descreva as expressões e as ações das pessoas. "
    "Transcreva qualquer texto visível exatamente como aparece. "
    "Mencione cores só quando elas importam para entender a imagem. "
    "Se for figurinha ou meme, explique a emoção ou a piada."
)
_MOTION = " Há vários quadros: descreva o movimento."


def image_prompt(detail="short", animated=False, question=""):
    question = (question or "").strip()
    if question:
        text = "Responda só a esta pergunta sobre a imagem, em português do Brasil, em poucas frases. " + _KIND
    elif detail == "long":
        text = "Descreva esta imagem em português do Brasil, com mais detalhes, em poucos parágrafos. " + _KIND
    else:
        text = "Descreva esta imagem em português do Brasil, em um parágrafo curto. " + _KIND
    if animated:
        text += _MOTION
    if question:
        text += "\n\nPergunta: " + question
    return text
