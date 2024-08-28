function myFunction(answer, message) {

  message.value = answer.value;
  
  };

  function answerRetarget(value_new, value_old, answer_text, button_edit_category, text_edit_category, button_answer) {

    if (value_new != value_old) {
      answer_text.placeholder = 'При смене категории укажите комментарий для сотрудников направления, которым переадресуется сообщение. И нажмите кнопку "Изменить категорию"'
      button_edit_category.style="display: inline-block;"
      text_edit_category.hidden=true
      button_answer.hidden=true
    } else {
      answer_text.placeholder = ''
      button_edit_category.style="display: none;"
      text_edit_category.hidden=false
      button_answer.hidden=false
    }
    
  }