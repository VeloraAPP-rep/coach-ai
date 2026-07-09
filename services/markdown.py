@dp.callback_query(F.data == "make_markdown")
async def handle_make_markdown(callback: types.CallbackQuery):
    await callback.answer()

    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    await callback.message.answer("Скачиваю аудио и делаю расшифровку. Это может занять несколько минут...")

    try:
        audio_filename, title = download_audio(url)
        segments = transcribe_audio(audio_filename)
        markdown_file = save_transcript_markdown(title, url, segments)

        await callback.message.answer_document(
            document=FSInputFile(markdown_file),
            caption=f"Готов Markdown: {title}"
        )

    except Exception as error:
        await callback.message.answer(f"Ошибка при создании Markdown:\n{error}")