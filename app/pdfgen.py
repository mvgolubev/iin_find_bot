from datetime import date
from pathlib import Path
from random import randint

from fpdf import FPDF


def generate_pdf(iin_data: dict, birth_date: date, birth_location: str) -> bytearray:
    birth_date_str = f"{birth_date:%d.%m.%Y}"
    if iin_data["kgd_date"]:
        kgd_date = date.fromisoformat(iin_data["kgd_date"])
        issue_date_str = f"{kgd_date:%d.%m.%Y}"
    else:
        issue_date_str = f"{date.today():%d.%m.%Y}"
    yy = issue_date_str[-2:]
    doc_number = f"00{yy}{str(randint(1,99999999)).zfill(8)}"

    font_family = "FreeSerif"
    font_regular = Path("app", "fonts", "FreeSerif.otf")
    font_bold = Path("app", "fonts", "FreeSerifBold.otf")
    font_italic = Path("app", "fonts", "FreeSerifItalic.otf")

    left_margin = 23
    top_margin = 20
    col_width = 125.6
    col2_x = left_margin + col_width

    pdf = FPDF(format="A4", orientation="landscape", unit="mm")
    pdf.set_author("Telegram Bot @iin_find_bot")
    pdf.set_creator("Telegram Bot @iin_find_bot")
    pdf.set_producer("Python fpdf2 library")
    pdf.set_title("Свидетельство о регистрации ИИН")
    pdf.set_subject("ИИН Казахстана")
    pdf.set_keywords("ИИН Казахстан")
    pdf.add_page()
    pdf.set_margins(left=left_margin, top=top_margin)

    pdf.add_font(family=font_family, style="", fname=font_regular)
    pdf.add_font(family=font_family, style="b", fname=font_bold)
    pdf.add_font(family=font_family, style="i", fname=font_italic)

    pdf.set_font(family="FreeSerif", size=18, style="b")
    pdf.cell(
        w=col_width,
        text=" Жеке сәйкестендіру нөмірін",
        align="C",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(w=col_width, h=1, border=False, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(style="b", size=14)
    pdf.cell(
        w=col_width,
        text=" тіркеу туралы куәлік",
        align="C",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(w=col_width, h=1, border=False, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(style="b", size=13)
    pdf.cell(
        w=col_width,
        text=f"{doc_number}",
        align="C",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(w=col_width, h=1, border=False, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(style="")
    pdf.cell(
        w=col_width,
        text=" Жеке Сәйкестендіру Нөмірі(ЖСН):",
        align="C",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(style="b", size=20)
    pdf.cell(
        w=col_width,
        h=18,
        text=f" {iin_data['iin']}",
        align="C",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Тегі   ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(
        h=6,
        text=iin_data["last_name"],
        align="L",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Аты    ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(
        h=6,
        text=iin_data["first_name"],
        align="L",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Әкесінің аты    ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(
        h=6,
        text=iin_data["middle_name"],
        align="L",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Туған күні   ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(
        h=6,
        text=f"{birth_date_str} ж.",
        align="L",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Туған жері   ", align="L", border=False)
    pdf.set_font(size=15)
    pdf.cell(
        h=6,
        text=birth_location,
        align="L",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(size=12)
    pdf.cell(h=6, text=" Берген мекеме   ", align="L", border=False)
    pdf.set_font(size=15)
    pdf.cell(
        h=6,
        text="ҚР Ішкі Істер министрлігі",
        align="L",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font(size=12)
    pdf.cell(h=6, text=" Берілген кезі   ", align="L", border=False)
    pdf.set_font(size=15)
    pdf.cell(
        h=6,
        text=f"{issue_date_str} ж.",
        align="L",
        border=False,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(w=col_width, h=15, border=False, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(style="i", size=10)
    pdf.cell(
        w=col_width,
        text="Жеке басты куәландыратын құжатты ұсынған кезде жарамды",
        align="L",
        border=False,
    )

    pdf.set_xy(col2_x, top_margin)
    pdf.set_font(style="b", size=18)
    pdf.cell(
        w=col_width,
        text="  Свидетельство о регистрации",
        align="C",
        border=False,
        new_x="LEFT",
        new_y="NEXT",
    )
    pdf.cell(w=col_width, h=1, border=False, new_x="LEFT", new_y="NEXT")
    pdf.set_font(style="b", size=14)
    pdf.cell(
        w=col_width,
        text="  индивидуального идентификационного номера",
        align="C",
        border=False,
        new_x="LEFT",
        new_y="NEXT",
    )
    pdf.set_font(style="b", size=13)
    pdf.cell(w=col_width, h=1, border=False, new_x="LEFT", new_y="NEXT")
    pdf.cell(
        w=col_width,
        text=f" {doc_number}",
        align="C",
        border=False,
        new_x="LEFT",
        new_y="NEXT",
    )
    pdf.cell(w=col_width, h=1, border=False, new_x="LEFT", new_y="NEXT")
    pdf.set_font(style="")
    pdf.cell(
        w=col_width,
        text=" Индивидуальный Идентификационный Номер(ИИН):",
        align="C",
        border=False,
        new_x="LEFT",
        new_y="NEXT",
    )
    pdf.set_font(style="b", size=20)
    pdf.cell(
        w=col_width,
        h=18,
        text=f" {iin_data['iin']}",
        align="C",
        border=False,
        new_x="LEFT",
        new_y="NEXT",
    )
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Фамилия   ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(
        h=6, text=f"{iin_data['last_name']}", align="L", border=False, new_y="NEXT"
    )
    pdf.set_x(col2_x)
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Имя    ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(
        h=6, text=f"{iin_data['first_name']}", align="L", border=False, new_y="NEXT"
    )
    pdf.set_x(col2_x)
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Отчество    ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(
        h=6, text=f"{iin_data['middle_name']}", align="L", border=False, new_y="NEXT"
    )
    pdf.set_x(col2_x)
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Дата рождения   ", align="L", border=False)
    pdf.set_font(style="b", size=15)
    pdf.cell(h=6, text=f"{birth_date_str} г.", align="L", border=False, new_y="NEXT")
    pdf.set_x(col2_x)
    pdf.set_font(style="", size=12)
    pdf.cell(h=6, text=" Место рождения   ", align="L", border=False)
    pdf.set_font(size=15)
    pdf.cell(
        h=6,
        text=birth_location,
        align="L",
        border=False,
        new_y="NEXT",
    )
    pdf.set_x(col2_x)
    pdf.set_font(size=12)
    pdf.cell(h=6, text=" Орган выдачи   ", align="L", border=False)
    pdf.set_font(size=15)
    pdf.cell(
        h=6,
        text="  Министерство внутренних дел РК",
        align="L",
        border=False,
        new_y="NEXT",
    )
    pdf.set_x(col2_x)
    pdf.set_font(size=12)
    pdf.cell(h=6, text=" Дата выдачи    ", align="L", border=False)
    pdf.set_font(size=15)
    pdf.cell(h=6, text=f"{issue_date_str} г.", align="L", border=False, new_y="NEXT")
    pdf.set_x(col2_x)
    pdf.cell(w=col_width, h=15, border=False, new_x="LEFT", new_y="NEXT")
    pdf.set_font(style="i", size=10)
    pdf.cell(
        w=col_width,
        text="Действительно только при предъявлении документа, удостоверяющего личность",
        align="L",
        border=False,
    )
    pdf_path = Path("app", "data", "pdf", f"iin_{iin_data['iin']}.pdf")
    return pdf.output(pdf_path)


if __name__ == "__main__":
    iin_data = {
    "last_name": "Сидоров",
    "first_name": "Иван",
    "middle_name": "Петрович",
    "iin": "001122345678",
    # "kgd_date": "2022-10-28",
    "kgd_date": None,
    }
    birth_date = date(1999, 9, 25)
    birth_location = "Россия   ГОРЬКОВСКАЯ"

    generate_pdf(iin_data, birth_date, birth_location)

    
