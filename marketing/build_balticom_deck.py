#!/usr/bin/env python3
"""build_balticom_deck.py — the written answer to Balticom's technical due-diligence questions.

Balticom (Latvia, top-3 ISP, ~110k subscribers, ~4,600 business sites) asked twelve questions
across five blocks before agreeing to a demo: which AI models, whose supply chain, can it run
locally, is customer data used for training, retention, where data is processed, GDPR roles,
human oversight, hallucination control, independent audit, access control and incident handling,
reference implementations with measurable KPIs, and team composition.

This deck answers them in the S4biz template. It reuses build_consensus_deck's Deck/card/bullets
helpers and build_consensus_business_deck's table helper, so the template exists in exactly ONE
implementation and the four S4biz decks cannot drift apart.

    python marketing/build_balticom_deck.py [--lang ru|en|both] [--out PATH]

FIVE RULES THIS DECK OBEYS:

1. EVERY NUMBER IS OURS AND MEASURED, OR CONTRACTUAL AND QUOTED FROM A DOCUMENT WE WILL SIGN.
   The service levels, retention periods, sub-processor list and breach-notification commitment
   are lifted from Cybergod_04_Service_Level_Agreement_EN and
   Cybergod_07_Data_Hosting_GDPR_Factsheet_EN. Nothing is rounded upward for effect.

2. NO INVENTED REFERENCE CUSTOMER AND NO INVENTED KPI DELTA. Balticom asked for two or three
   implementations with measurable results. We have two we can evidence: cybergod.ai, which is
   ours and public, and a sovereign secure-mobile programme, which is real and whose customer is
   NOT NAMED anywhere in this file. A contact-centre KPI delta we have not measured is not put on
   a slide; the pilot is how that number gets created.

3. THE HONEST GAPS ARE ON THEIR OWN SLIDE. No ISO 27001, no SOC 2, the inference region to be
   confirmed in writing. A due-diligence pack is the worst possible place to over-claim, and a
   buyer who finds the gap himself stops believing the rest of the document.

4. NO EM DASH, anywhere in customer-facing copy (standing rule, operator, 10 Aug 2026).

5. BILINGUAL FROM ONE SOURCE. Every string is T(ru, en) inline, so a translation cannot drift
   away from its original and no key space can go stale. Same doctrine as legal.jsx.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_consensus_deck import (  # noqa: E402  — one template implementation, reused
    AMBER, BODY, CYAN, Deck, DISPLAY, GREEN, INDIGO, INK, LINE, MONO, MUTED, PANEL, RED, TEXT,
    VIOLET, WHITE, _rect, _tb, bullets, card, stat,
)
from build_consensus_business_deck import table  # noqa: E402

LANG = "ru"


def T(ru, en):
    return ru if LANG == "ru" else en


# The title row is arithmetic, not taste: 0.70in at 30pt Arial Black, and a second line lands on
# the sub-heading at y=1.55. Measured on the render, same guard as the business deck.
TITLE_MAX = 50


def _guard(d):
    orig = d.slide

    def guarded(eyebrow, title, title_tail=None, sub=None, footer="", hero=False):
        if not hero:
            n = len(title) + len(title_tail or "")
            if n > TITLE_MAX:
                raise SystemExit("[X] title is %d chars and wraps onto the sub-heading: %r"
                                 % (n, title + (title_tail or "")))
        return orig(eyebrow, title, title_tail, sub, footer, hero)

    d.slide = guarded
    return d


def build(template, out):
    FOOT = T("S4BIZ GROUP · CYBERGOD LLC · ПОДГОТОВЛЕНО ДЛЯ BALTICOM · КОНФИДЕНЦИАЛЬНО",
             "S4BIZ GROUP · CYBERGOD LLC · PREPARED FOR BALTICOM · CONFIDENTIAL")
    d = _guard(Deck(template))

    # =========================================================================================
    # 01 — TITLE
    # =========================================================================================
    s = d.slide(T("S4biz · Cybergod · ответы на технические вопросы · август 2026",
                  "S4biz · Cybergod · answers to the technical questions · August 2026"),
                [(T("ДВЕНАДЦАТЬ ВОПРОСОВ.", "TWELVE QUESTIONS."), WHITE),
                 (T("ДВЕНАДЦАТЬ ОТВЕТОВ.", "TWELVE ANSWERS."), VIOLET),
                 (T("БЕЗ МАРКЕТИНГА.", "NO MARKETING."), CYAN)],
                footer=FOOT, hero=True)
    _tb(s, 0.57, 4.45, 11.60, 0.60,
        T("Balticom попросил разобраться в архитектуре до демонстрации. Это правильный порядок, "
          "поэтому документ построен как ответ по пунктам, а не как презентация продукта. "
          "Там, где у нас нет доказательства, так и написано.",
          "Balticom asked to understand the architecture before a demo. That is the right order, "
          "so this document is built as a point-by-point answer rather than a product pitch. "
          "Where we have no evidence, the slide says so."), 12, BODY, TEXT, space=1.3)
    for i, (v, lab, col) in enumerate([
            ("4", T("модели · четыре разных\nвендора, без общей точки отказа",
                    "models · four separate\nvendors, no shared failure"), CYAN),
            ("0", T("данных клиента уходит\nна обучение моделей",
                    "customer data used to\ntrain or fine-tune models"), VIOLET),
            ("EU", T("Франкфурт FRA1 или\nваше железо, on-prem",
                     "Frankfurt FRA1 or\nyour own hardware, on-prem"), INDIGO),
            ("99.5%", T("доступность в месяц\nпо подписанному SLA",
                        "monthly availability\nunder a signed SLA"), GREEN),
            (T("24ч", "24h"), T("на уведомление об\nинциденте безопасности",
                      "to notify a security\nincident, contractual"), AMBER)]):
        x = 0.55 + i * 2.49
        _rect(s, x, 5.45, 2.29, 1.35, INK, LINE)
        _rect(s, x, 5.45, 2.29, 0.06, col, None)
        _tb(s, x + 0.16, 5.61, 1.99, 0.50, v, 22, col, DISPLAY, True)
        _tb(s, x + 0.16, 6.07, 2.05, 0.66, lab, 8.5, WHITE, TEXT, True, space=1.15)

    # =========================================================================================
    # 02 — THE FIVE ANSWERS ON ONE PAGE
    # =========================================================================================
    s = d.slide(T("сводка · пять блоков вопросов", "summary · five blocks of questions"),
                T("КОРОТКО: ", "IN SHORT: "), T("ПЯТЬ ОТВЕТОВ", "FIVE ANSWERS"),
                T("Каждая строка раскрыта на отдельном слайде. Номер справа.",
                  "Each line is opened up on its own slide. The number is on the right."), FOOT)
    table(s, 0.55, 2.15, 12.23,
          [T("блок вопросов", "question block"), T("короткий ответ", "the short answer"),
           T("слайд", "slide")],
          [[T("1 · Модели и архитектура", "1 · Models and architecture"),
            T("Мы не разработчик моделей. Четыре модели четырёх вендоров с открытыми весами. "
              "Развёртывание в EU, в вашем облаке или полностью у вас.",
              "We are not a model developer. Four open-weight models from four vendors. "
              "Deployed in the EU, in your own cloud, or entirely on your premises."), "03 · 05"],
           [T("2 · Данные и обучение", "2 · Data and training"),
            T("Обучения на ваших данных нет ни у нас, ни у поставщика. Это техническое свойство "
              "конструкции и обязательство в DPA. Журналы 30 дней, документы 90 дней.",
              "No training on your data, by us or by the provider. That is a property of the "
              "design and a commitment in the DPA. Logs 30 days, documents 90 days."), "06 · 07"],
           [T("3 · Безопасность и контроль", "3 · Security and control"),
            T("Модели советуют, решает детерминированный код. Аудитор всегда другого вендора. "
              "Независимой сертификации у нас сегодня нет, и мы это пишем прямо.",
              "Models advise, deterministic code decides. The auditor is always a different "
              "vendor. We hold no independent certification today and we say so."), "08 · 11"],
           [T("4 · Опыт и результаты", "4 · Experience and results"),
            T("Два внедрения, которые мы можем показать. Придуманных KPI по чужим проектам "
              "здесь нет. Вашу базовую линию меряем на пилоте, вашими же системами.",
              "Two deployments we can evidence. No invented KPI deltas from other people's "
              "projects. Your baseline is measured during the pilot, in your own systems."),
            "12 · 13"],
           [T("5 · Команда и поддержка", "5 · Team and support"),
            T("Роли, уровни поддержки и время реакции зафиксированы в SLA: S1 за час, "
              "восстановление за четыре часа, эскалация на главного архитектора поимённо.",
              "Roles, support tiers and response times are fixed in the SLA: S1 in one hour, "
              "restore in four, escalation to a named principal architect."), "14"]],
          [0.20, 0.665, 0.135], rh=0.86, size=9.6)

    # =========================================================================================
    # 03 — BLOCK 1: WHICH MODELS, WHOSE SUPPLY CHAIN
    # =========================================================================================
    s = d.slide(T("блок 1 · какие модели и чья цепочка поставки",
                  "block 1 · which models and whose supply chain"),
                T("МОДЕЛИ: ", "MODELS: "), T("МЫ НЕ ВЕНДОР", "WE ARE NOT A VENDOR"),
                T("Мы не обучаем и не дообучаем модели. Мы строим слой, который их проверяет.",
                  "We do not train or fine-tune models. We build the layer that checks them."),
                FOOT)
    table(s, 0.55, 2.10, 12.23,
          [T("модель", "model"), T("вендор", "vendor"), T("лицензия", "licence"),
           T("роль в цепочке", "role in the chain")],
          [["deepseek-3.2", "DeepSeek", T("открытые веса", "open weights"),
            T("автор разбора · голова цепочки, выбрана по замеру на реальном запросе",
              "author · head of the chain, chosen by measurement on the real prompt")],
           ["llama-4-maverick", "Meta", T("открытые веса", "open weights"),
            T("второй автор · независимая формулировка того же материала",
              "second author · an independent write-up of the same material")],
           ["gemma-4-31B-it", "Google", T("открытые веса", "open weights"),
            T("аудитор · ищет ошибки в работе автора, никогда не своего вендора",
              "auditor · attacks the author's work, never its own vendor")],
           ["kimi-k2.6", "Moonshot AI", T("открытые веса", "open weights"),
            T("аудитор · четвёртый вендор как страховка от отказа провайдера",
              "auditor · a fourth vendor as insurance against a provider outage")]],
          [0.19, 0.13, 0.14, 0.54], rh=0.52, size=9.4)
    _rect(s, 0.55, 4.60, 3.95, 2.20, INK, LINE)
    _tb(s, 0.81, 4.80, 3.45, 0.24, T("ПОЧЕМУ ЧЕТЫРЕ", "WHY FOUR"), 9, CYAN, MONO, True)
    _tb(s, 0.81, 5.12, 3.45, 1.55,
        T("Одна модель это одна обучающая выборка, один набор слепых зон и один режим отказа. "
          "Когда она ошибается, она ошибается уверенно и связным текстом. Четыре вендора не имеют "
          "общей точки отказа: сбой или лимит у провайдера не выключает панель.",
          "One model is one training corpus, one set of blind spots and one failure mode. When it "
          "is wrong it is wrong confidently, in fluent prose. Four vendors share no failure "
          "domain: an outage or a rate limit at one provider does not silence the panel."),
        9.5, BODY, TEXT, space=1.3)
    _rect(s, 4.69, 4.60, 3.95, 2.20, INK, LINE)
    _tb(s, 4.95, 4.80, 3.45, 0.24, T("ЦЕПОЧКА ПОСТАВКИ", "THE SUPPLY CHAIN"), 9, VIOLET, MONO,
        True)
    _tb(s, 4.95, 5.12, 3.45, 1.55,
        T("Веса всех четырёх моделей опубликованы. Сегодня они вызываются через бессерверный "
          "инференс DigitalOcean; ту же цепочку можно поднять на своём железе через vLLM без "
          "изменения кода. Список моделей это переменная окружения, а не архитектура.",
          "All four sets of weights are published. Today they are called through DigitalOcean "
          "serverless inference; the same chain runs on your own hardware through vLLM with no "
          "code change. The model list is an environment variable, not an architecture."),
        9.5, BODY, TEXT, space=1.3)
    _rect(s, 8.83, 4.60, 3.95, 2.20, PANEL, LINE)
    _tb(s, 9.09, 4.80, 3.45, 0.24, T("БЕЗ ПРИВЯЗКИ К ВЕНДОРУ", "NO VENDOR LOCK-IN"), 9, GREEN,
        MONO, True)
    _tb(s, 9.09, 5.12, 3.45, 1.55,
        T("Порядок цепочки определяется замером на реальном запросе, а не предпочтением. "
          "Мы уже меняли голову цепочки по результатам замеров дважды. Если завтра появится "
          "модель лучше или дешевле, она встаёт в цепочку без переписывания системы.",
          "The order of the chain is set by measurement on the real prompt, not by preference. We "
          "have already changed the head of the chain twice on evidence. If a better or cheaper "
          "model appears tomorrow, it joins the chain without rewriting the system."),
        9.5, BODY, TEXT, space=1.3)

    # =========================================================================================
    # 04 — BLOCK 1: THE ARCHITECTURE
    # =========================================================================================
    s = d.slide(T("блок 1 · архитектура решения", "block 1 · solution architecture"),
                T("АРХИТЕКТУРА: ", "ARCHITECTURE: "), T("КОД РЕШАЕТ", "CODE DECIDES"),
                T("ИИ пишет и проверяет. Побочные действия выполняет детерминированный код.",
                  "AI writes and verifies. Side effects are executed by deterministic code."),
                FOOT)
    steps = [("01", T("СБОР", "COLLECT"),
              T("только публичные\nисточники, без пакетов\nв ваш периметр",
                "public sources only,\nno packets sent into\nyour perimeter"), CYAN),
             ("02", T("2 АВТОРА", "2 AUTHORS"),
              T("две модели пишут\nразбор независимо\nдруг от друга",
                "two models write the\nanalysis independently\nof each other"), INDIGO),
             ("03", T("2 АУДИТОРА", "2 AUDITORS"),
              T("другие вендоры ищут\nошибки, самопроверка\nзапрещена",
                "different vendors attack\nthe result; self-review\nis forbidden"), VIOLET),
             ("04", T("ПРОВЕРКА", "VERIFY"),
              T("каждый идентификатор\nсверяется с собранными\nдоказательствами",
                "every identifier is\nchecked against the\nevidence collected"), AMBER),
             ("05", T("РЕШЕНИЕ", "DECIDE"),
              T("детерминированные\nпроверки, а не голос\nмодели",
                "deterministic checks,\nnot a model's\nvote"), GREEN),
             ("06", T("ЖУРНАЛ", "LOG"),
              T("модель, токены, цена,\nзадержка, кто победил\nв цепочке",
                "model, tokens, cost,\nlatency, which model\nwon the chain"), CYAN)]
    for i, (num, head, body, col) in enumerate(steps):
        x = 0.55 + i * 2.08
        _rect(s, x, 2.20, 1.92, 1.80, INK, LINE)
        _rect(s, x, 2.20, 1.92, 0.05, col, None)
        _tb(s, x + 0.18, 2.38, 1.56, 0.26, num, 12, col, DISPLAY, True)
        _tb(s, x + 0.18, 2.70, 1.66, 0.30, head, 10.5, WHITE, DISPLAY, True)
        _tb(s, x + 0.18, 3.06, 1.70, 0.85, body, 8.2, BODY, TEXT, space=1.25)
        if i < 5:
            _tb(s, x + 1.90, 2.90, 0.20, 0.24, ">", 12, LINE, MONO, True)
    _rect(s, 0.55, 4.25, 12.23, 1.15, PANEL, LINE)
    _tb(s, 0.85, 4.43, 11.63, 0.24,
        T("ПРАВИЛО, КОТОРОЕ ДЕЛАЕТ ЭТО ПРОВЕРЯЕМЫМ", "THE RULE THAT MAKES THIS CHECKABLE"),
        10, CYAN, MONO, True)
    _tb(s, 0.85, 4.76, 11.63, 0.60,
        T("Модель никогда не решает, выполнить ли действие. Она пишет текст и выносит суждение, "
          "а запускает, применяет или блокирует только код по заранее утверждённому списку. "
          "В защищённой мобильной платформе автоматически выполняются лишь действия из белого "
          "списка: изолировать устройство, отозвать сертификат, разорвать сессию.",
          "A model never decides whether an action runs. It writes text and forms a judgement; "
          "only code executes, applies or blocks, and only from a list approved in advance. In "
          "the secure mobile platform, exactly three actions execute automatically: isolate a "
          "device, revoke a certificate, drop a session."), 10.5, BODY, TEXT, space=1.3)
    bullets(s, 0.55, 5.62, 5.95, [
        T("Обмен с моделью это строгий JSON-контракт: пустой или сломанный ответ отклоняется "
          "за секунды, и очередь переходит к следующему вендору.",
          "The exchange with a model is a strict JSON contract: an empty or malformed answer is "
          "rejected in seconds and the queue moves to the next vendor."),
        T("Ответ модели, который прошёл разбор, но пуст по существу, считается отказом. "
          "Покрытие меряется глубиной текста, а не фактом ответа.",
          "An answer that parses but says nothing counts as a failure. Coverage is measured by "
          "the depth of the text, not by the fact that a reply arrived.")], gap=0.50, size=9.6)
    bullets(s, 6.83, 5.62, 5.95, [
        T("Если внешний источник недоступен, система пишет «неизвестно» и не превращает "
          "отсутствие данных в вывод о слабости.",
          "If an external source is unreachable, the system writes 'unknown' and never turns "
          "missing data into a conclusion about a weakness."),
        T("Каждый вызов модели попадает в журнал вместе с ценой. За всё время работы средняя "
          "стоимость инференса на одну оценку составила около $0.005.",
          "Every model call is logged with its price. Across the platform's life the average "
          "inference cost per assessment is about $0.005.")], gap=0.50, size=9.6)

    # =========================================================================================
    # 05 — BLOCK 1: DEPLOYMENT OPTIONS
    # =========================================================================================
    s = d.slide(T("блок 1 · локально или в облаке", "block 1 · on-premises or cloud"),
                T("ТРИ ВАРИАНТА ", "THREE DEPLOYMENT "), T("РАЗВЁРТЫВАНИЯ", "OPTIONS"),
                T("Третий вариант уже работает в другом проекте: две площадки, инференс на месте.",
                  "The third option is live in another programme: two sites, inference on site."),
                FOOT)
    table(s, 0.55, 2.10, 12.23,
          [T("вариант", "option"), T("где данные", "where the data is"),
           T("кто вызывает модель", "who calls the model"),
           T("доступ вендора", "vendor access"), T("срок", "lead time")],
          [[T("A · Наше облако EU", "A · Our EU cloud"),
            T("Франкфурт FRA1, реплик за пределами ЕС нет",
              "Frankfurt FRA1, no replication outside the EU"),
            T("бессерверный инференс, получает только технические факты",
              "serverless inference, receives technical facts only"),
            T("операторы платформы, обязательство о конфиденциальности",
              "platform operators, bound by confidentiality"), T("дни", "days")],
           [T("B · Ваш арендатор", "B · Your tenant"),
            T("ваша подписка облака, ваш регион и ваши ключи",
              "your cloud subscription, your region, your keys"),
            T("вызов из вашей сети, endpoint выбираете вы",
              "called from your network, you choose the endpoint"),
            T("только на время работ, по вашему доступу",
              "only during agreed work, under your access"), T("недели", "weeks")],
           [T("C · Полностью у вас", "C · Fully on-premises"),
            T("ваше железо, при необходимости без выхода в интернет",
              "your hardware, air-gapped if required"),
            T("vLLM на ваших GPU, наружу не уходит ничего",
              "vLLM on your GPUs, nothing leaves the building"),
            T("нет постоянного доступа, обновления по вашему каналу",
              "no standing access, updates through your channel"),
            T("месяцы", "months")]],
          [0.16, 0.23, 0.25, 0.24, 0.12], rh=0.74, size=9.2)
    _rect(s, 0.55, 4.95, 6.05, 1.85, INK, LINE)
    _tb(s, 0.81, 5.13, 5.55, 0.24, T("ЭТО НЕ ГИПОТЕЗА", "THIS IS NOT A HYPOTHESIS"), 9, GREEN,
        MONO, True)
    _tb(s, 0.81, 5.45, 5.55, 1.25,
        T("Вариант C уже построен в суверенной защищённой мобильной платформе: 150 устройств, "
          "две независимые площадки в юрисдикции заказчика, инференс на месте через vLLM, "
          "две модели пишут разбор инцидента и две проверяют его независимо. Заказчика мы не "
          "называем; архитектуру покажем на технической сессии.",
          "Option C is already built in a sovereign secure mobile platform: 150 devices, two "
          "independent sites inside the customer's jurisdiction, inference on site through vLLM, "
          "two models writing the incident analysis and two verifying it independently. We do not "
          "name that customer; we will walk the architecture at the technical session."),
        9.6, BODY, TEXT, space=1.3)
    _rect(s, 6.73, 4.95, 6.05, 1.85, PANEL, LINE)
    _tb(s, 6.99, 5.13, 5.55, 0.24, T("ЧТО ЭТО ЗНАЧИТ ДЛЯ ОПЕРАТОРА СВЯЗИ",
                                     "WHAT THIS MEANS FOR AN OPERATOR"), 9, CYAN, MONO, True)
    _tb(s, 6.99, 5.45, 5.55, 1.25,
        T("Локализация данных перестаёт быть договорным обещанием и становится свойством схемы: "
          "если модель работает на вашем железе, данных, которые могли бы уйти к третьей стороне, "
          "просто нет. Вопрос о регионе обработки у поставщика инференса в этом варианте "
          "не возникает вовсе.",
          "Data residency stops being a contractual promise and becomes a property of the "
          "diagram: if the model runs on your hardware, there is no data that could reach a third "
          "party at all. In this option the question of the inference provider's processing "
          "region does not arise."), 9.6, BODY, TEXT, space=1.3)

    # =========================================================================================
    # 06 — BLOCK 2: DATA AND TRAINING
    # =========================================================================================
    s = d.slide(T("блок 2 · защита и использование данных",
                  "block 2 · data protection and use"),
                T("ДАННЫЕ: ", "DATA: "), T("ОБУЧЕНИЯ НЕ БУДЕТ", "NO TRAINING ON YOURS"),
                T("Гарантия из двух частей: то, что записано в договоре, и то, что следует из схемы.",
                  "A guarantee in two parts: what the contract says, and what the design implies."),
                FOOT)
    card(s, 0.55, 2.05, 3.95, 2.35, T("ответ", "answer"), GREEN,
         T("Нет, не используются", "No, they are not"),
         T("Мы не обучаем, не дообучаем и не строим модели на данных клиентов. Обязательство "
           "зафиксировано в соглашении об обработке данных по статье 28 GDPR, а не только в "
           "маркетинговом тексте.",
           "We do not train, fine-tune or build models on customer data. The commitment sits in "
           "the Article 28 GDPR data processing agreement, not only in a marketing sentence."),
         bsize=9.6)
    card(s, 4.69, 2.05, 3.95, 2.35, T("что вообще уходит", "what actually leaves"), CYAN,
         T("Только технические факты", "Technical facts only"),
         T("В модель уходит содержание разбора: технические находки и текст задачи. Личность "
           "пользователя, его почта и IP-адрес в модель не передаются никогда. Персональные "
           "данные ваших сотрудников до модели не доходят.",
           "What goes to the model is the material of the analysis: technical findings and the "
           "task text. A user identity, e-mail address or IP address is never passed. Your "
           "people's personal data does not reach a model at all."), bsize=9.6)
    card(s, 8.83, 2.05, 3.95, 2.35, T("техническая гарантия", "the technical guarantee"), VIOLET,
         T("Вариант C снимает вопрос", "Option C removes it"),
         T("Договор можно нарушить, схему нарушить нельзя. При инференсе на вашем железе третьей "
           "стороны в цепочке нет, поэтому и обучать на ваших данных некому. Это самый сильный "
           "ответ, который мы можем дать.",
           "A contract can be breached; a diagram cannot. With inference on your hardware there "
           "is no third party in the chain, so there is nobody who could train on your data. "
           "That is the strongest answer we can give."), bsize=9.6)
    _tb(s, 0.55, 4.58, 12.23, 0.26, T("СРОКИ ХРАНЕНИЯ И МЕСТО ОБРАБОТКИ, КАК В ДОГОВОРЕ",
                                      "RETENTION AND LOCATION, AS WRITTEN IN THE CONTRACT"),
        10, CYAN, MONO, True)
    # rh 0.44 put the last row's zebra band at 7.11, across the footer line at 7.04. Measured on
    # the render, not guessed: four rows from 5.30 at 0.40 end at 6.90.
    table(s, 0.55, 4.90, 12.23,
          [T("данные", "data"), T("зачем", "why"), T("срок", "retention"), T("где", "where")],
          [[T("Адрес пользователя платформы", "Platform user e-mail address"),
            T("контроль доступа и второй фактор", "access control and second factor"),
            T("пока есть доступ", "while access exists"), "FRA1"],
           [T("IP, время, браузер, страна", "IP, timestamp, browser, country"),
            T("обнаружение атак", "attack detection"), T("до 30 дней", "up to 30 days"), "FRA1"],
           [T("Отчёты и результаты работы", "Reports and generated deliverables"),
            T("выдача результата и прослеживаемость", "delivery and traceability"),
            T("90 дней", "90 days"), "FRA1"],
           [T("Резервные копии", "Backups"), T("восстановление", "recovery"),
            T("7 дней · RPO 24ч · RTO 8ч", "7 days · RPO 24h · RTO 8h"),
            T("в пределах ЕС", "within the EU")]],
          [0.30, 0.30, 0.25, 0.15], rh=0.40, size=9.2)

    # =========================================================================================
    # 07 — BLOCK 2: GDPR ROLES AND TRANSFERS
    # =========================================================================================
    s = d.slide(T("блок 2 · роли по GDPR и передачи",
                  "block 2 · GDPR roles and transfers"),
                T("GDPR: ", "GDPR: "), T("РОЛИ И ПЕРЕДАЧИ", "ROLES AND TRANSFERS"),
                T("Полный перечень субобработчиков. Других участников в цепочке нет.",
                  "The complete sub-processor list. There is nobody else in the chain."), FOOT)
    roles = [(T("BALTICOM", "BALTICOM"), T("Контролёр", "Controller"),
              T("Определяет цели и средства обработки. Отвечает за уведомление своего надзорного "
                "органа в течение 72 часов по статье 33.",
                "Determines the purposes and means. Responsible for notifying its own supervisory "
                "authority within 72 hours under Article 33."), CYAN),
             (T("STARS4BUSINESS OÜ", "STARS4BUSINESS OÜ"), T("Обработчик", "Processor"),
              T("Обрабатывает только по вашим документированным указаниям. Уведомляет вас об "
                "инциденте в течение 24 часов с момента, как узнал.",
                "Processes only on your documented instructions. Notifies you of an incident "
                "within 24 hours of becoming aware of it."), VIOLET),
             (T("ПОСТАВЩИК ИНФЕРЕНСА", "INFERENCE PROVIDER"), T("Субобработчик", "Sub-processor"),
              T("Получает технические находки и текст задачи. Личности пользователя не получает. "
                "В варианте C отсутствует полностью.",
                "Receives technical findings and task text. Receives no user identity. In "
                "option C it is absent entirely."), INDIGO)]
    for i, (who, role, body, col) in enumerate(roles):
        x = 0.55 + i * 4.14
        _rect(s, x, 2.05, 3.95, 1.95, INK, LINE)
        _rect(s, x, 2.05, 3.95, 0.06, col, None)
        _tb(s, x + 0.26, 2.25, 3.45, 0.24, who, 9, col, MONO, True)
        _tb(s, x + 0.26, 2.55, 3.45, 0.32, role, 15, WHITE, DISPLAY, True)
        _tb(s, x + 0.26, 3.00, 3.45, 0.90, body, 9.4, BODY, TEXT, space=1.3)
        if i < 2:
            _tb(s, x + 3.98, 2.85, 0.16, 0.24, ">", 12, LINE, MONO, True)
    _tb(s, 0.55, 4.14, 12.23, 0.26, T("ПОЛНЫЙ СПИСОК СУБОБРАБОТЧИКОВ",
                                      "THE COMPLETE SUB-PROCESSOR LIST"), 10, CYAN, MONO, True)
    # Three rows at 0.62 from 4.95 ended at 6.81 and the note panel starts at 6.50, so the last
    # row was drawn under it. Start higher and shorten the row.
    table(s, 0.55, 4.45, 12.23,
          [T("субобработчик", "sub-processor"), T("что делает", "what it does"),
           T("где", "location"), T("основание передачи", "transfer basis")],
          [["DigitalOcean, LLC", T("хостинг и инфраструктура", "hosting and infrastructure"),
            T("Франкфурт FRA1, Германия", "Frankfurt FRA1, Germany"),
            T("обработка в ЕС", "processing inside the EU")],
           ["Google LLC (Gmail API)",
            T("доставляет одноразовый код входа, получает только адрес почты",
              "delivers the one-time login code, receives the e-mail address only"), "USA",
            T("EU-US Data Privacy Framework, ст. 45, с переходом на SCC при отмене",
              "EU-US Data Privacy Framework, Art. 45, with a fallback to the SCCs")],
           [T("Бессерверный инференс", "Serverless AI inference"),
            T("пишет деловой текст отчёта, личности пользователя не получает",
              "writes the business prose, receives no user identity"),
            T("регион подтверждаем письменно", "region confirmed in writing"),
            T("персональных данных пользователей не передаётся",
              "no personal data of platform users is transmitted")]],
          [0.19, 0.34, 0.17, 0.30], rh=0.53, size=9.0)
    _rect(s, 0.55, 6.50, 12.23, 0.42, PANEL, LINE)
    _tb(s, 0.85, 6.59, 11.63, 0.26,
        T("Ни аналитики, ни рекламных сетей, ни обогащения CRM, ни брокеров данных в цепочке нет. "
          "Право на аудит и ответ на ваш опросник в течение 30 дней записаны в DPA.",
          "There is no analytics provider, no advertising network, no CRM enrichment and no data "
          "broker in the chain. An audit right and a 30-day answer to your questionnaire are "
          "written into the DPA."), 9.4, BODY, TEXT)

    # =========================================================================================
    # 08 — BLOCK 3: HUMAN OVERSIGHT AND HALLUCINATION
    # =========================================================================================
    s = d.slide(T("блок 3 · участие человека и точность",
                  "block 3 · human oversight and accuracy"),
                T("ЧЕЛОВЕК И ", "THE HUMAN AND "), T("ГАЛЛЮЦИНАЦИИ", "THE HALLUCINATION"),
                T("Промпт это просьба, а не гарантия. Поэтому у каждого правила есть код-проверка.",
                  "A prompt is a request, not a guarantee. So every rule has a check behind it."),
                FOOT)
    bullets(s, 0.55, 2.10, 6.05, [
        T("Аудитор никогда не той же модели и не того же вендора, что автор. Самопроверка "
          "запрещена кодом: система скорее откажется от аудита, чем проверит себя сама.",
          "The auditor is never the same model or the same vendor as the author. Self-review is "
          "forbidden in code: the system refuses to audit rather than audit itself."),
        T("Аудитор может пометить вывод, но не может его удалить в одиночку. Удаление проходит "
          "только если детерминированные данные подтверждают ошибку, и есть предел: аудитор не "
          "может обнулить отчёт.",
          "The auditor may flag a finding but cannot delete it alone. A deletion happens only "
          "where deterministic data confirms the error, and there is a ceiling: the auditor "
          "cannot empty a report."),
        T("Каждый идентификатор, который модель написала в текст, сверяется с фактически "
          "собранными доказательствами. Неподтверждённый удаляется, текст сохраняется, событие "
          "попадает в журнал.",
          "Every identifier the model writes into the text is cross-checked against the evidence "
          "actually collected. An unverifiable one is stripped, the prose is kept and an event is "
          "recorded."),
        T("Отсутствие данных никогда не становится выводом. Неудачный запрос к внешнему источнику "
          "даёт «неизвестно», а не «у клиента нет защиты».",
          "Missing data never becomes a conclusion. A failed lookup yields 'unknown', never 'the "
          "customer has no control here'.")], gap=0.52, size=9.8)
    _rect(s, 6.83, 2.10, 5.95, 2.55, INK, LINE)
    _tb(s, 7.09, 2.30, 5.45, 0.24, T("ГДЕ ЗДЕСЬ ЧЕЛОВЕК", "WHERE THE HUMAN SITS"), 9, CYAN, MONO,
        True)
    _tb(s, 7.09, 2.62, 5.45, 1.90,
        T("Три точки, и все три обязательные.\n\n"
          "1 · Постановка задачи. Прогон запускает named-пользователь из белого списка; кто "
          "запустил и что именно, видно в журнале.\n"
          "2 · Разбор результата. Результат это документ для человека, а не автоматическое "
          "действие в вашей системе.\n"
          "3 · Утверждение действия. Всё, что меняет состояние, выполняется по заранее "
          "согласованному списку или руками оператора.",
          "Three points, and all three are mandatory.\n\n"
          "1 · Framing. A run is started by a named user from the allow-list; who started it and "
          "what they asked is visible in the log.\n"
          "2 · Review. The result is a document for a person, not an automatic action inside your "
          "systems.\n"
          "3 · Approval. Anything that changes state runs from a list agreed in advance, or by "
          "an operator's hand."), 9.6, BODY, TEXT, space=1.28)
    _rect(s, 0.55, 4.80, 12.23, 2.00, PANEL, LINE)
    _tb(s, 0.85, 4.98, 11.63, 0.24,
        T("ЧЕСТНО О ГРАНИЦЕ: ЧТО ЭТО НЕ УБИРАЕТ",
          "HONESTLY ABOUT THE LIMIT: WHAT THIS DOES NOT REMOVE"), 10, AMBER, MONO, True)
    _tb(s, 0.85, 5.32, 11.63, 1.35,
        T("Консенсус снижает вероятность уверенной ошибки, но не превращает язык в истину. "
          "Мы можем показать это на своих же данных: за время эксплуатации панель четырёх моделей "
          "поймала дефекты, которые не видел ни один человек, и в тех же прогонах предлагала "
          "исправления для несуществующих подсистем. Именно поэтому решение принимает код, "
          "а не голосование моделей, и именно поэтому мы не обещаем ноль ошибок. "
          "Мы обещаем, что ошибка модели не станет действием без проверки.",
          "Consensus lowers the odds of a confident error; it does not turn language into truth. "
          "We can show this on our own data: over the platform's life the four-model panel caught "
          "defects no human had seen, and in the same runs proposed fixes for subsystems that do "
          "not exist. That is exactly why code decides rather than a vote of models, and why we "
          "do not promise zero errors. We promise that a model's error does not become an action "
          "without a check."), 10.5, BODY, TEXT, space=1.35)

    # =========================================================================================
    # 09 — BLOCK 3: THE CATCH LEDGER
    # =========================================================================================
    s = d.slide(T("блок 3 · чем это подтверждается", "block 3 · what backs this up"),
                T("ЧТО ПАНЕЛЬ ", "WHAT THE PANEL "), T("ПОЙМАЛА", "CAUGHT"),
                T("Реальные находки из журнала выпусков, вместе с промахами той же панели.",
                  "Real entries from the release log, together with that panel's own misses."),
                FOOT)
    rows = [(T("ПОЙМАЛА", "CAUGHT"), GREEN,
             T("Аудитор опознал хеш пустой строки в ответе служебного интерфейса и по одному "
               "этому значению определил, что административный API отключён. Ни один человек "
               "в ревью этого не заметил.",
               "An auditor recognised the hash of the empty string in a service response and, "
               "from that value alone, identified a disabled admin API. No human reviewer had "
               "noticed it.")),
            (T("ПОЙМАЛА", "CAUGHT"), GREEN,
             T("Дважды панель заметила, что проверка сообщает «пройдено», а её же пояснение "
               "описывает отказ. Оба раза сломанной была проверка, а не система. Это самый "
               "опасный класс дефекта: зелёный индикатор поверх поломки.",
               "Twice the panel noticed a check reporting 'pass' while its own detail described a "
               "failure. Both times the check was broken, not the system. That is the most "
               "dangerous class of defect: a green light over a fault.")),
            (T("ПОЙМАЛА", "CAUGHT"), GREEN,
             T("Панель указала, что доступность и аутентификация административного интерфейса "
               "нигде не проверяются. Этот интерфейс способен заменить конфигурацию всех "
               "доменов на сервере. Появилась отдельная проверка из соседнего контейнера.",
               "The panel pointed out that the admin interface's reachability and authentication "
               "were never verified. That interface can replace the running configuration of "
               "every domain on the host. A cross-container probe now exists.")),
            (T("ОШИБЛАСЬ", "WAS WRONG"), RED,
             T("Одна модель трижды подряд описывала уже удалённый механизм проверки как "
               "действующий, другая предложила манифест Kubernetes для системы, где Kubernetes "
               "нет. Панель сильна там, где видит доказательства, и слаба там, где достраивает "
               "архитектуру по памяти.",
               "One model described a removed mechanism as current three runs in a row; another "
               "proposed a Kubernetes manifest for a system that has no Kubernetes. The panel is "
               "strong where it can see evidence and weak where it extrapolates architecture "
               "from memory."))]
    y = 2.15
    for i, (tag, col, body) in enumerate(rows):
        h = 1.02
        _rect(s, 0.55, y, 12.23, h, INK if i % 2 == 0 else PANEL, LINE)
        _rect(s, 0.55, y, 0.05, h, col, None)
        _tb(s, 0.85, y + 0.16, 1.55, 0.24, tag, 9, col, MONO, True)
        _tb(s, 2.55, y + 0.14, 10.00, 0.80, body, 9.8, BODY, TEXT, space=1.32)
        y += h + 0.10
    _tb(s, 0.55, 6.58, 12.23, 0.30,
        T("Вывод, который мы делаем сами: панель это сигнал, а не власть. Единогласный отказ "
          "четырёх моделей против зелёного результата проверок останавливает выпуск и требует "
          "решения человека.",
          "The conclusion we draw ourselves: the panel is a signal, not an authority. A unanimous "
          "refusal by four models against a green set of checks halts the release and requires a "
          "human decision."), 9.6, AMBER, TEXT)

    # =========================================================================================
    # 10 — BLOCK 3: ACCESS, LOGS, INCIDENTS
    # =========================================================================================
    s = d.slide(T("блок 3 · доступ, аудит-логи, инциденты",
                  "block 3 · access control, audit logs, incidents"),
                T("ДОСТУП, ЖУРНАЛЫ, ", "ACCESS, LOGS, "), T("ИНЦИДЕНТЫ", "INCIDENTS"),
                T("Всё перечисленное это условия договора, а не описание намерений.",
                  "Everything below is a contract term, not a statement of intent."), FOOT)
    card(s, 0.55, 2.05, 3.95, 2.30, T("контроль доступа", "access control"), CYAN,
         T("Три барьера подряд", "Three barriers in a row"),
         T("Войти может только адрес из белого списка. К нему общий пароль и шестизначный код в "
           "тот же почтовый ящик: знать пароль недостаточно, нужно владеть почтой. Сессия живёт "
           "12 часов, пять неверных попыток блокируют вход на 15 минут. Документы видит только "
           "тот, кто их создал.",
           "Only an allow-listed address can log in. On top of that a shared password and a "
           "six-digit code to that same mailbox: knowing the password is not enough, you must "
           "control the inbox. Sessions last 12 hours; five wrong attempts lock login for 15 "
           "minutes. Deliverables are visible only to the person who created them."), bsize=9.2)
    card(s, 4.69, 2.05, 3.95, 2.30, T("аудит и наблюдаемость", "audit and observability"), VIOLET,
         T("Событие на каждое действие", "An event for every action"),
         T("Вход, запуск оценки, обращение к модели и ошибка пишутся структурированными "
           "событиями и хранятся до 30 дней. Одиннадцать правил обнаружения работают постоянно: "
           "неудачные входы, перебор паролей и кодов, всплески запросов, сканирование путей, "
           "нетипичные загрузки, вход с нового адреса.",
           "Logins, assessment runs, model calls and errors are written as structured events and "
           "kept up to 30 days. Eleven detection rules run continuously: failed logins, password "
           "spraying, code brute-forcing, request floods, path probing, unusual downloads and "
           "logins from a new address."), bsize=9.2)
    card(s, 8.83, 2.05, 3.95, 2.30, T("реакция на инцидент", "incident response"), AMBER,
         T("Сроки в SLA, не в переписке", "Timings in the SLA"),
         T("S1: реакция за 1 час, восстановление за 4. S2: 4 рабочих часа и 1 рабочий день. "
           "Уведомление о нарушении безопасности в течение 24 часов с момента, как мы узнали; "
           "обновления не реже раза в сутки, письменный разбор причин в течение 10 рабочих дней "
           "после закрытия.",
           "S1: one-hour response, four-hour restore. S2: four business hours and one business "
           "day. A security breach is notified within 24 hours of us becoming aware; updates at "
           "least daily; a written root-cause report within 10 business days of closure."),
         bsize=9.2)
    _tb(s, 0.55, 4.60, 12.23, 0.26, T("ЧТО ЕЩЁ РАБОТАЕТ ПОСТОЯННО",
                                      "WHAT ELSE RUNS CONTINUOUSLY"), 10, CYAN, MONO, True)
    bullets(s, 0.55, 4.95, 6.05, [
        T("Код проверяется до выпуска: поиск секретов, статический анализ безопасности и "
          "сканирование образов. Провал блокирует выпуск, а не пишет замечание.",
          "Code is checked before it ships: secret scanning, static security analysis and image "
          "scanning. A failure blocks the release rather than filing a note."),
        T("Сервер обновляется автоматически каждые три дня, сначала резервная копия, затем "
          "патч. Перед перезагрузкой конфигурация проверяется на валидность.",
          "The server patches automatically every three days, backup first, patch second. Before "
          "a reboot the configuration is validated."),
        T("Внешний мониторинг работает вне сервера, каждые 10 минут, включая срок действия "
          "сертификата: наблюдение изнутри отказавшего периметра бесполезно.",
          "External monitoring runs off the box every 10 minutes, including certificate expiry: "
          "monitoring from inside a failed perimeter is useless.")], gap=0.52, size=9.5)
    bullets(s, 6.83, 4.95, 5.95, [
        T("Доступ снимается конфигурацией, а не выпуском версии, поэтому отзыв действует сразу.",
          "Access is removed by configuration, not by a software release, so a revocation takes "
          "effect at once."),
        T("Геолокация только до уровня страны, из локальной базы: ни один внешний сервис "
          "геолокации не вызывается. IP можно хранить солёными хешами по вашему требованию.",
          "Geolocation is country-level only, from a local database: no external geolocation "
          "service is ever called. IP addresses can be stored as salted hashes on request."),
        T("Выгрузка журналов и отчёт о доступности предоставляются по запросу в течение 10 "
          "рабочих дней.",
          "Log exports and an availability report are provided on request within 10 business "
          "days.")], gap=0.52, size=9.5)

    # =========================================================================================
    # 11 — BLOCK 3: INDEPENDENT AUDIT, HONESTLY
    # =========================================================================================
    s = d.slide(T("блок 3 · независимый аудит безопасности",
                  "block 3 · independent security audit"),
                T("НЕЗАВИСИМЫЙ АУДИТ: ", "INDEPENDENT AUDIT: "), T("ЧЕСТНО", "HONESTLY"),
                T("Документ о защите данных это худшее место для преувеличений.",
                  "A data-protection document is the worst possible place to over-claim."), FOOT)
    _rect(s, 0.55, 2.05, 5.95, 2.45, INK, LINE)
    _rect(s, 0.55, 2.05, 5.95, 0.06, RED, None)
    _tb(s, 0.81, 2.28, 5.45, 0.24, T("ЧЕГО У НАС НЕТ", "WHAT WE DO NOT HAVE"), 9, RED, MONO, True)
    _tb(s, 0.81, 2.62, 5.45, 1.75,
        T("Stars4business OÜ сегодня не имеет ISO/IEC 27001, SOC 2 или эквивалентной "
          "сертификации по этой платформе. Если ваш опросник поставщика спрашивает об этом, "
          "ответ именно такой.\n\n"
          "Отчёта независимого пентеста платформы, пригодного для передачи вам, у нас "
          "на сегодня тоже нет.",
          "Stars4business OÜ does not today hold ISO/IEC 27001, SOC 2 or any equivalent "
          "certification for this platform. If your supplier questionnaire asks, that is the "
          "answer.\n\n"
          "We also do not today hold an independent penetration-test report on the platform that "
          "we could hand to you."), 10, BODY, TEXT, space=1.32)
    _rect(s, 6.83, 2.05, 5.95, 2.45, INK, LINE)
    _rect(s, 6.83, 2.05, 5.95, 0.06, GREEN, None)
    _tb(s, 7.09, 2.28, 5.45, 0.24, T("ЧТО МЫ МОЖЕМ ПОКАЗАТЬ", "WHAT WE CAN EVIDENCE"), 9, GREEN,
        MONO, True)
    _tb(s, 7.09, 2.62, 5.45, 1.75,
        T("Технические и организационные меры по статье 32 в приложении 3 к DPA, как договорное "
          "обязательство. Право на аудит для заказчика и ответ на ваш опросник в течение 30 дней. "
          "Автоматические ворота выпуска, которые блокируют релиз. Сертификаты дата-центра во "
          "Франкфурте запрашиваются через нас.",
          "The Article 32 technical and organisational measures in Annex 3 of the DPA, as a "
          "contractual commitment. A customer audit right and a 30-day answer to your "
          "questionnaire. Automated release gates that block a release. The Frankfurt data "
          "centre's own certifications can be requested through us."), 10, BODY, TEXT, space=1.32)
    _rect(s, 0.55, 4.70, 12.23, 2.10, PANEL, LINE)
    _tb(s, 0.85, 4.90, 11.63, 0.24, T("ЧТО МЫ ПРЕДЛАГАЕМ СДЕЛАТЬ С ЭТИМ",
                                      "WHAT WE PROPOSE TO DO ABOUT IT"), 10, CYAN, MONO, True)
    bullets(s, 0.85, 5.25, 11.63, [
        T("Ваша служба безопасности проводит собственное ревью до пилота. Мы отвечаем на ваш "
          "опросник письменно и предоставляем DPA с приложением о мерах защиты.",
          "Your security function runs its own review before the pilot. We answer your "
          "questionnaire in writing and provide the DPA with its measures annex."),
        T("Пентест пилотной установки заказывается у независимого подрядчика. Мы готовы, чтобы "
          "подрядчика выбрал Balticom, и чтобы отчёт шёл вам напрямую.",
          "A penetration test of the pilot deployment is commissioned from an independent firm. "
          "We are content for Balticom to choose that firm and for the report to go to you "
          "directly."),
        T("Сертификация по ISO/IEC 27001 включается в план как отдельная работа со сроком, а не "
          "как обещание в переписке. Обсуждаем на технической сессии.",
          "ISO/IEC 27001 certification is put into the plan as a scoped piece of work with a "
          "date, not as a promise in correspondence. To be discussed at the technical session.")],
        gap=0.50, size=10)

    # =========================================================================================
    # 12 — BLOCK 4: TWO DEPLOYMENTS
    # =========================================================================================
    s = d.slide(T("блок 4 · практический опыт", "block 4 · practical experience"),
                T("ДВА ВНЕДРЕНИЯ, ", "TWO DEPLOYMENTS, "), T("БЕЗ ЛЕГЕНД", "NO LEGENDS"),
                T("Одно можно открыть прямо сейчас. Второе описываем без имени заказчика.",
                  "One you can open right now. The second is described without its customer."),
                FOOT)
    _rect(s, 0.55, 2.05, 6.05, 3.05, INK, LINE)
    _rect(s, 0.55, 2.05, 6.05, 0.06, CYAN, None)
    _tb(s, 0.81, 2.28, 5.55, 0.24, T("ВНЕДРЕНИЕ 01 · ОТКРЫТО", "DEPLOYMENT 01 · PUBLIC"), 9, CYAN,
        MONO, True)
    _tb(s, 0.81, 2.58, 5.55, 0.34, "cybergod.ai", 15, WHITE, DISPLAY, True)
    _tb(s, 0.81, 3.00, 5.55, 2.00,
        T("Наша собственная промышленная платформа: внешняя оценка защищённости и проверка "
          "соответствия по названию компании, четыре модели, четыре языка документов, шесть "
          "языков интерфейса. Работает в эксплуатации, а не в демо-стенде.\n\n"
          "Всё, что описано в этом документе, работает именно там: цепочка моделей, аудитор "
          "другого вендора, журнал стоимости, ворота выпуска. Вы можете открыть сайт и "
          "посмотреть публичную демонстрацию без регистрации.",
          "Our own production platform: external exposure assessment and compliance grading from "
          "a company name, four models, four document languages, six interface languages. In "
          "production, not on a demo stand.\n\n"
          "Everything described in this document runs there: the model chain, the "
          "different-vendor auditor, the cost ledger, the release gate. You can open the site and "
          "view the public demonstration without registering."), 9.6, BODY, TEXT, space=1.3)
    for i, (v, lab) in enumerate([("190+", T("оценок выполнено", "assessments run")),
                                  ("$0.005", T("инференс на оценку", "inference per run")),
                                  ("43", T("проверки до выпуска", "pre-release checks"))]):
        stat(s, 0.81 + i * 1.90, 5.20, 1.80, v, lab, CYAN, vsize=19)
    _rect(s, 6.73, 2.05, 6.05, 3.05, INK, LINE)
    _rect(s, 6.73, 2.05, 6.05, 0.06, VIOLET, None)
    _tb(s, 6.99, 2.28, 5.55, 0.24, T("ВНЕДРЕНИЕ 02 · ЗАКАЗЧИК НЕ НАЗЫВАЕТСЯ",
                                     "DEPLOYMENT 02 · CUSTOMER NOT NAMED"), 9, VIOLET, MONO, True)
    _tb(s, 6.99, 2.58, 5.55, 0.34,
        T("Суверенная защищённая мобильная платформа", "Sovereign secure mobile platform"),
        13, WHITE, DISPLAY, True)
    _tb(s, 6.99, 3.00, 5.55, 2.00,
        T("150 устройств на открытой ОС, две независимые площадки в юрисдикции заказчика, "
          "инференс на месте. Открытый стек целиком: Ubuntu Touch, Matrix, Asterisk, LiveKit, "
          "Wazuh, vLLM.\n\n"
          "Роль ИИ там ровно та же, что мы предлагаем вам: две модели пишут разбор события, две "
          "независимо проверяют, аудитор всегда другого вендора, автоматически выполняются лишь "
          "действия из белого списка. Каждый вызов в журнале: модель, токены, цена.",
          "150 devices on an open OS, two independent sites inside the customer's jurisdiction, "
          "inference on site. A fully open stack: Ubuntu Touch, Matrix, Asterisk, LiveKit, Wazuh, "
          "vLLM.\n\n"
          "The AI plays exactly the role we are proposing to you: two models write the incident "
          "analysis, two verify it independently, the auditor is always a different vendor, and "
          "only whitelisted actions execute automatically. Every call is logged: model, tokens, "
          "cost."), 9.6, BODY, TEXT, space=1.3)
    for i, (v, lab) in enumerate([("150", T("устройств в парке", "devices in the fleet")),
                                  ("2", T("площадки в стране", "sites in-country")),
                                  ("0", T("данных наружу", "data leaves the country"))]):
        stat(s, 6.99 + i * 1.90, 5.20, 1.80, v, lab, VIOLET, vsize=19)
    _rect(s, 0.55, 6.28, 12.23, 0.62, PANEL, LINE)
    _tb(s, 0.85, 6.38, 11.63, 0.45,
        T("Чего здесь нет намеренно: чужих KPI по контакт-центру, которые мы не измеряли сами. "
          "Balticom спрашивает про среднее время обслуживания, FCR, NPS и конверсию. Это ваши "
          "числа, и получить их можно только на ваших данных. Как именно, на следующем слайде.",
          "What is deliberately absent: contact-centre KPI figures from other people's projects "
          "that we did not measure ourselves. Balticom asks about average handling time, FCR, NPS "
          "and conversion. Those are your numbers, and they can only be produced on your data. "
          "How, on the next slide."), 9.6, AMBER, TEXT, space=1.25)

    # =========================================================================================
    # 13 — BLOCK 4: HOW THE KPI GETS MEASURED
    # =========================================================================================
    s = d.slide(T("блок 4 · измеримые результаты", "block 4 · measurable results"),
                T("KPI: ", "KPI: "), T("МЕРИМ ВАШУ БАЗУ", "WE MEASURE YOUR BASELINE"),
                T("Восемь недель, одна очередь обращений, критерии приёмки согласованы заранее.",
                  "Eight weeks, one queue, acceptance criteria agreed in advance."), FOOT)
    ph = [("01", T("НЕДЕЛИ 1-2", "WEEKS 1-2"), T("БАЗОВАЯ ЛИНИЯ", "BASELINE"),
           T("Снимаем текущие значения в ваших системах, без нашего участия в измерении. "
             "Пока нет базы, любой прирост это мнение.",
             "Current values are taken from your systems, with no involvement from us in the "
             "measurement. Without a baseline any uplift is an opinion."), CYAN),
          ("02", T("НЕДЕЛИ 3-8", "WEEKS 3-8"), T("ПИЛОТ", "PILOT"),
           T("Одна очередь обращений или один процесс. Ограниченная область даёт чистое "
             "сравнение и понятную стоимость отката.",
             "One queue or one process. A narrow scope gives a clean comparison and a "
             "predictable cost of rollback."), VIOLET),
          ("03", T("НЕДЕЛЯ 9", "WEEK 9"), T("ПРИЁМКА", "ACCEPTANCE"),
           T("Сравнение с базой по согласованным порогам. Не достигли порога, не переходим "
             "к промышленной эксплуатации.",
             "Comparison against the baseline on the agreed thresholds. If a threshold is "
             "missed, we do not move to production."), GREEN)]
    for i, (num, when, head, body, col) in enumerate(ph):
        x = 0.55 + i * 4.14
        _rect(s, x, 2.05, 3.95, 1.75, INK, LINE)
        _rect(s, x, 2.05, 3.95, 0.06, col, None)
        _tb(s, x + 0.26, 2.25, 3.45, 0.24, when, 9, col, MONO, True)
        _tb(s, x + 0.26, 2.55, 3.45, 0.32, head, 14, WHITE, DISPLAY, True)
        _tb(s, x + 0.26, 2.98, 3.45, 0.75, body, 9.4, BODY, TEXT, space=1.3)
    _tb(s, 0.55, 4.00, 12.23, 0.26, T("ЧТО ИМЕННО МЕРИМ И ЧЕМ", "WHAT IS MEASURED, AND WITH WHAT"),
        10, CYAN, MONO, True)
    # Five rows at 0.46 from 4.75 ended at 7.05, one hundredth of an inch across the footer.
    table(s, 0.55, 4.30, 12.23,
          [T("показатель", "metric"), T("источник данных", "source of the number"),
           T("почему он честный", "why it is honest")],
          [[T("Среднее время обслуживания", "Average handling time"),
            T("ваша телефония и CRM", "your telephony and CRM"),
            T("измеряется вашей системой, мы к цифре не прикасаемся",
              "measured by your system; we never touch the figure")],
           [T("Решение с первого обращения", "First contact resolution"),
            T("ваши тикеты, повторные обращения за 7 дней",
              "your tickets, repeat contacts within 7 days"),
            T("определение фиксируется до пилота, а не после результата",
              "the definition is fixed before the pilot, not after the result")],
           [T("Доля обращений без оператора", "Contacts resolved without an agent"),
            T("логи бота и переводы на человека", "bot logs and hand-offs to a human"),
            T("перевод на оператора считается неуспехом, а не отказом клиента",
              "a hand-off counts as a miss, not as the customer giving up")],
           [T("CSAT и NPS", "CSAT and NPS"), T("ваш опрос, ваша методика", "your survey, your method"),
            T("выборку и вопрос не меняем, иначе сравнение бессмысленно",
              "the sample and the question do not change, or the comparison is meaningless")],
           [T("Стоимость обращения", "Cost per contact"),
            T("ваша себестоимость плюс наш счёт за инференс",
              "your unit cost plus our inference invoice"),
            T("стоимость ИИ видна по журналу вызовов, а не оценочно",
              "the AI cost comes from the call ledger, not from an estimate")]],
          [0.26, 0.30, 0.44], rh=0.42, size=9.2)

    # =========================================================================================
    # 14 — BLOCK 5: TEAM AND SUPPORT
    # =========================================================================================
    s = d.slide(T("блок 5 · команда, роли и поддержка", "block 5 · team, roles and support"),
                T("КОМАНДА ", "THE TEAM "), T("И ПОДДЕРЖКА", "AND SUPPORT"),
                T("Уровни поддержки и время реакции взяты из подписываемого SLA.",
                  "Support tiers and response times are taken from the SLA we sign."), FOOT)
    bullets(s, 0.55, 2.10, 6.05, [
        T("Главный архитектор: архитектура, цепочка моделей, ворота выпуска, третья линия "
          "эскалации поимённо в SLA.",
          "Principal architect: architecture, the model chain, the release gates, and the named "
          "third line of escalation in the SLA."),
        T("Инженеры платформы: движок оценки, бэкенд, интерфейс, конвейер выпуска и "
          "автоматические проверки.",
          "Platform engineers: the assessment engine, backend, interface, release pipeline and "
          "the automated checks."),
        T("Инженеры по моделям: контракт обмена, замеры цепочки на реальных запросах, стоимость "
          "и качество ответов.",
          "Model engineers: the exchange contract, chain measurement on real prompts, cost and "
          "answer quality."),
        T("Интеграция: подключение к вашей телефонии, CRM и каталогу пользователей; работы на "
          "площадке при варианте C.",
          "Integration: connecting to your telephony, CRM and directory; on-site work under "
          "option C."),
        T("Безопасность и эксплуатация: доступы, наблюдаемость, реагирование, обновления, "
          "работа с вашим опросником поставщика.",
          "Security and operations: access, observability, response, patching and answering your "
          "supplier questionnaire.")], gap=0.54, size=9.8)
    _tb(s, 6.83, 2.10, 5.95, 0.26, T("УРОВНИ ПОДДЕРЖКИ ПО SLA", "SUPPORT LEVELS UNDER THE SLA"),
        10, CYAN, MONO, True)
    table(s, 6.83, 2.45, 5.95,
          [T("уровень", "sev"), T("реакция", "response"), T("восстановление", "restore")],
          [["S1", T("1 час", "1 hour"), T("4 часа", "4 hours")],
           ["S2", T("4 рабочих часа", "4 business hours"), T("1 рабочий день", "1 business day")],
           ["S3", T("1 рабочий день", "1 business day"),
            T("следующий релиз", "next release")],
           ["S4", T("2 рабочих дня", "2 business days"), T("по согласованию", "by agreement")]],
          [0.18, 0.42, 0.40], rh=0.40, size=9.4)
    _tb(s, 6.83, 4.45, 5.95, 0.90,
        T("Каналы: почта как основной и создающий тикет, Telegram для быстрой сортировки, "
          "телефон для эскалации S1. Часы поддержки 09:00-18:00 CET по рабочим дням, "
          "круглосуточно по S1 для уровня OEM и Platinum.",
          "Channels: e-mail as the primary channel that creates the ticket, Telegram for fast "
          "triage, telephone for S1 escalation. Support hours 09:00-18:00 CET on business days, "
          "24x7 for Severity 1 on the OEM and Platinum tiers."), 9.4, BODY, TEXT, space=1.3)
    _rect(s, 0.55, 5.60, 12.23, 1.20, PANEL, LINE)
    _tb(s, 0.85, 5.78, 11.63, 0.24, T("ЗАПОЛНИТЬ ПЕРЕД ОТПРАВКОЙ", "TO BE FILLED BEFORE SENDING"),
        10, AMBER, MONO, True)
    _tb(s, 0.85, 6.10, 11.63, 0.60,
        T("Численность выделенной команды на этот проект: [__] человек, из них разработка [__], "
          "интеграция [__], поддержка [__]. Мы намеренно не ставим сюда число, пока состав не "
          "закреплён: цифра в документе такого рода становится обязательством.",
          "Dedicated team size for this project: [__] people, of whom engineering [__], "
          "integration [__], support [__]. We deliberately leave the number blank until the "
          "staffing is fixed: a figure in a document of this kind becomes a commitment."),
        10.5, BODY, TEXT, space=1.3)

    # =========================================================================================
    # 15 — WHAT WE DO NOT CLAIM
    # =========================================================================================
    s = d.slide(T("границы · то, что обычно выясняется поздно",
                  "limits · what usually surfaces too late"),
                T("ЧЕГО МЫ ", "WHAT WE DO "), T("НЕ УТВЕРЖДАЕМ", "NOT CLAIM"),
                T("Список короткий и полный. Если найдёте шестой пункт, скажите нам.",
                  "The list is short and complete. If you find a sixth item, tell us."), FOOT)
    lims = [(T("Сертификаций нет", "No certifications"),
             T("ISO/IEC 27001, SOC 2 или эквивалента у нас на сегодня нет. Есть договорные меры "
               "по статье 32, право на аудит и готовность к вашему пентесту.",
               "We hold no ISO/IEC 27001, SOC 2 or equivalent today. What exists is the Article "
               "32 measures as a contract term, an audit right and a readiness for your "
               "penetration test.")),
            (T("Это не пентест", "This is not a penetration test"),
             T("Оценка cybergod.ai читает только публичные источники. Ни одного пакета в ваш "
               "периметр, ни сканирования портов, ни попыток входа, ни агента, ни ваших "
               "учётных данных.",
               "The cybergod.ai assessment reads public sources only. Not one packet into your "
               "perimeter, no port scanning, no login attempts, no agent and none of your "
               "credentials.")),
            (T("Отсутствие находки не есть безопасность",
               "The absence of a finding is not security"),
             T("Отчёт описывает то, что видно в публичных источниках на момент прогона. "
               "Полноту находок мы не гарантируем и прямо пишем это в SLA.",
               "A report describes what is visible in public sources at the time of the run. We "
               "do not warrant that findings are complete, and the SLA says so.")),
            (T("Суммы в евро это модель", "Euro figures are a model"),
             T("Финансовые величины в отчётах это смоделированные диапазоны с показанными "
               "допущениями, а не измерения. Разделы про соответствие это конспект первичных "
               "правовых текстов, а не юридическая консультация.",
               "Financial figures in the reports are modelled ranges with the assumptions shown, "
               "not measurements. The compliance sections summarise primary legal texts and are "
               "not legal advice.")),
            (T("Чужих KPI у нас нет", "We have no third-party KPI"),
             T("Названного заказчика в контакт-центре с опубликованной дельтой KPI мы вам "
               "сегодня не покажем. Именно поэтому предлагается пилот с измерением вашей базы.",
               "We cannot show you a named contact-centre customer with a published KPI delta "
               "today. That is exactly why the proposal is a pilot that measures your own "
               "baseline."))]
    # Five rows at 0.90 + 0.09 ran to 6.96 and the closing line at 6.62 was drawn across the last
    # card. 0.84 + 0.07 ends the last card at 6.58.
    y = 2.10
    for i, (head, body) in enumerate(lims):
        h = 0.84
        _rect(s, 0.55, y, 12.23, h, INK if i % 2 == 0 else PANEL, LINE)
        _rect(s, 0.55, y, 0.05, h, AMBER, None)
        _tb(s, 0.90, y + 0.14, 3.55, 0.55, head, 11.5, WHITE, DISPLAY, True, space=1.1)
        _tb(s, 4.70, y + 0.14, 7.85, 0.66, body, 9.6, BODY, TEXT, space=1.28)
        y += h + 0.07
    _tb(s, 0.55, 6.66, 12.23, 0.30,
        T("Мы пишем это в первом документе, а не после подписания, потому что каждый из "
          "пунктов всё равно выясняется, и лучше от нас.",
          "We put this in the first document rather than after signature, because every item "
          "surfaces anyway, and it is better that it comes from us."), 9.6, MUTED, TEXT)

    # =========================================================================================
    # 16 — NEXT STEPS
    # =========================================================================================
    s = d.slide(T("следующий шаг · три пункта", "next step · three items"),
                T("ЧТО ДАЛЬШЕ: ", "NEXT: "), T("ТРИ ШАГА", "THREE STEPS"),
                T("Ни один из них не требует от Balticom доступа в свои системы.",
                  "None of them requires Balticom to grant access to its systems."), FOOT)
    nxt = [("01", T("ВЗАИМНОЕ NDA", "MUTUAL NDA"),
            T("Готово, подписывается за один оборот. После него мы показываем архитектуру "
              "второго внедрения с именем заказчика и деталями площадок.",
              "Ready, signed in one turn. After it we can show the architecture of the second "
              "deployment, with the customer named and the sites described."), CYAN),
           ("02", T("ТЕХНИЧЕСКАЯ СЕССИЯ, 60 МИНУТ", "TECHNICAL SESSION, 60 MINUTES"),
            T("Ваши ИТ и безопасность против нашего архитектора. Приносите свой опросник "
              "поставщика: письменный ответ в течение 30 дней зафиксирован в DPA.",
              "Your IT and security against our architect. Bring your supplier questionnaire: a "
              "written answer within 30 days is fixed in the DPA."), VIOLET),
           ("03", T("ПИЛОТ НА ВОСЕМЬ НЕДЕЛЬ", "AN EIGHT-WEEK PILOT"),
            T("Две недели базовой линии, шесть недель на одной очереди, пороги приёмки "
              "согласованы до старта. Область работ и стоимость фиксируются в SoW.",
              "Two weeks of baseline, six weeks on one queue, acceptance thresholds agreed "
              "before the start. Scope and price fixed in a statement of work."), GREEN)]
    for i, (num, head, body, col) in enumerate(nxt):
        x = 0.55 + i * 4.14
        _rect(s, x, 2.15, 3.95, 2.45, INK, LINE)
        _rect(s, x, 2.15, 3.95, 0.06, col, None)
        _tb(s, x + 0.26, 2.38, 3.45, 0.30, num, 13, col, DISPLAY, True)
        _tb(s, x + 0.26, 2.78, 3.45, 0.60, head, 13, WHITE, DISPLAY, True, space=1.05)
        _tb(s, x + 0.26, 3.50, 3.45, 1.00, body, 9.6, BODY, TEXT, space=1.3)
    _rect(s, 0.55, 4.85, 12.23, 1.95, PANEL, LINE)
    _tb(s, 0.85, 5.05, 5.55, 0.24, T("КОНТАКТ", "CONTACT"), 10, CYAN, MONO, True)
    _tb(s, 0.85, 5.38, 5.55, 1.20,
        "Evgeny Vainshtein\n"
        + T("Главный архитектор, Stars4business OÜ\n", "Principal Architect, Stars4business OÜ\n")
        + "feranicus@s4biz.io · WhatsApp +351 939 994 642\nwww.cybergod.ai",
        11, BODY, TEXT, space=1.35)
    _tb(s, 6.95, 5.05, 5.83, 0.24, T("ЧТО МЫ ПРИНЕСЁМ НА СЕССИЮ", "WHAT WE BRING TO THE SESSION"),
        10, GREEN, MONO, True)
    _tb(s, 6.95, 5.38, 5.83, 1.25,
        T("Соглашение об обработке данных с приложением о мерах защиты, SLA, справку о хостинге "
          "и GDPR, схему трёх вариантов развёртывания и живой прогон платформы по домену, "
          "который назовёте вы.",
          "The data processing agreement with its measures annex, the SLA, the hosting and GDPR "
          "factsheet, the three deployment diagrams, and a live run of the platform against a "
          "domain that you name."), 10.5, BODY, TEXT, space=1.35)

    return d.save(out)


def main():
    global LANG
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--lang", default="both", choices=["ru", "en", "both"])
    ap.add_argument("--template", default=os.path.join(
        here, "S4biz_Sovereign_Cyber_Cloud_Capability_Brief.pptx"))
    ap.add_argument("--outdir", default=here)
    a = ap.parse_args()

    langs = ["ru", "en"] if a.lang == "both" else [a.lang]
    for lang in langs:
        LANG = lang
        out = os.path.join(a.outdir, "S4biz_Balticom_Technical_Answers_%s.pptx" % lang.upper())
        print("built: %s" % build(a.template, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
