Feature: Продвинутый календарь

  #@startgantt
  #Project starts 2025-03-01
  #2025-03-08 to 2025-03-09 are named [Выходные]
  #2025-03-08 to 2025-03-09 are colored in #FFAAAA
  #-- До связывания FinishStart --
  #[Первая задача] starts 2025-03-01 and ends 2025-03-03 and is colored in GreenYellow/Green
  #[Вторая задача] starts 2025-03-10 and ends 2025-03-14 and is colored in GreenYellow/Green
  #
  #-- После связывания FinishStart --
  #
  #[Первая задача ] starts 2025-03-01 and ends 2025-03-03 and is colored in GreenYellow/Green
  #then [Вторая задача ] starts 2025-03-04 and ends 2025-03-10 and is colored in GreenYellow/Green
  #@endgantt

  @Scheduling
  Scenario: Две задачи последовательно, пересчёт дат второй связанной задачи со смещением влево
    Given cоздана задача "Первая задача" c датами "2025-03-01", "2025-03-03"
    And cоздана задача "Вторая задача" c датами "2025-03-10", "2025-03-14"
    When я связываю задачу "Первая задача" с задачей "Вторая задача" как "FinishStart"
    Then задача "Вторая задача" имеет дату начала:"2025-03-04", дату окончания:"2025-03-10"
