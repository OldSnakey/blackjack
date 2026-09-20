import random
import tkinter
import time


def load_images(card_images):
    suits = ["heart", "club", "diamond", "spade"]
    face_cards = ["jack", "queen", "king"]

    # For each suit, retrieve the image for the cards
    for suit in suits:
        # First load the number cards 1 to 10, 1 = ACE
        for card in range(1, 11):
            name = "cards/{}_{}.png".format(str(card), suit)
            image = tkinter.PhotoImage(file=name)
            card_images.append((card, image))

        # Next load the face cards
        for card in face_cards:
            name = "cards/{}_{}.png".format(card, suit)
            image = tkinter.PhotoImage(file=name)
            card_images.append((10, image))


def reset():
    global deck
    # Create a new deck of cards and shuffle
    deck = list(cards)
    random.shuffle(deck)

    # Reset the lists to store the dealer and player hands
    dealer_hand.clear()
    player_hand.clear()

    # Reset the frames holding the cards
    for child in dealer_card_frame.winfo_children():
        child.destroy()
    for child in player_card_frame.winfo_children():
        child.destroy()

    # Reset the scores
    first_deal()

    # Reset the result
    result_text.set("")

    # Reset the buttons
    dealer_button.configure(state="normal")
    player_button.configure(state="normal")


def score_hand(hand):
    # Calculate the total score of all cards in the list
    score = 0
    ace = False
    for card in hand:
        value = card
        if value == 1 and not ace:
            ace = True
            value = 11
        score += value
        # if we would bust, treat ace as 1 if possible
        if score > 21 and ace:
            score -= 10
            ace = False
    return score


def deal_card(frame):
    # Pop the next card off the top of the deck
    next_card = deck.pop(0)
    # Add the image to a label and display the label
    tkinter.Label(frame, image=next_card[1], relief="raised").pack(side="left")
    # Return the card value
    return next_card[0]


def first_deal():
    dealer_hand.append(deal_card(dealer_card_frame))
    dealer_score_label.set(score_hand(dealer_hand))
    player_hand.append(deal_card(player_card_frame))
    player_hand.append(deal_card(player_card_frame))
    player_score_label.set(score_hand(player_hand))


def deal_dealer():
    while dealer_score_label.get() < 17:
        dealer_hand.append(deal_card(dealer_card_frame))
        dealer_score_label.set(score_hand(dealer_hand))
        time.sleep(1)
        main_window.update()
    if player_score_label.get() > 21:
        result_text.set("You bust, dealer wins!")
        dealer_wins_text.set(dealer_wins_text.get() + 1)
        dealer_button.configure(state="disabled")
        player_button.configure(state="disabled")
    elif dealer_score_label.get() > 21 or dealer_score_label.get() < player_score_label.get():
        result_text.set("Player WINS!")
        player_wins_text.set(player_wins_text.get() + 1)
        dealer_button.configure(state="disabled")
        player_button.configure(state="disabled")
    elif dealer_score_label.get() > player_score_label.get():
        result_text.set("The dealer wins!")
        dealer_wins_text.set(dealer_wins_text.get() + 1)
        dealer_button.configure(state="disabled")
        player_button.configure(state="disabled")
    else:
        result_text.set("It's a draw")


def deal_player():
    player_hand.append(deal_card(player_card_frame))
    player_score_label.set(score_hand(player_hand))
    if player_score_label.get() > 21:
        result_text.set("You bust, dealer wins!")
        dealer_wins_text.set(dealer_wins_text.get() + 1)
        dealer_button.configure(state="disabled")
        player_button.configure(state="disabled")


def play_game():
    global deck
    global cards
    global dealer_button
    global player_button
    global dealer_hand
    global player_hand
    global dealer_wins_text
    global player_wins_text
    global result_text
    global main_window
    global player_score_label
    global dealer_score_label
    global player_card_frame
    global dealer_card_frame

    # Set up the screen and frames for the dealer and player
    main_window = tkinter.Tk()
    main_window.title("Blackjack")
    main_window.geometry("640x480")
    main_window.configure(background="green", padx=10, pady=10)

    # Player and Dealer win counter
    scoreboard_frame = tkinter.Frame(main_window, background="green")
    scoreboard_frame.grid(row=0, column=0, columnspan=3)

    tkinter.Label(scoreboard_frame, text="Dealer Wins:", background="green", fg="white").grid(row=0, column=0)
    dealer_wins_text = tkinter.IntVar()
    dealer_wins = tkinter.Label(scoreboard_frame, textvariable=dealer_wins_text, background="green", fg="white")
    dealer_wins.grid(row=0, column=1)

    tkinter.Label(scoreboard_frame, text="Player Wins:", background="green", fg="white").grid(row=0, column=2)
    player_wins_text = tkinter.IntVar()
    player_wins = tkinter.Label(scoreboard_frame, textvariable=player_wins_text, background="green", fg="white")
    player_wins.grid(row=0, column=3)

    result_text = tkinter.StringVar()
    result = tkinter.Label(scoreboard_frame, textvariable=result_text, background="green", fg="white")
    result.grid(row=1, column=0, columnspan=4)

    # Card playing area
    card_frame = tkinter.Frame(main_window, relief="sunken", borderwidth=1, background="green")
    card_frame.grid(row=1, column=0, sticky="ew", columnspan=3, rowspan=2)

    dealer_score_label = tkinter.IntVar()

    tkinter.Label(card_frame, text="Dealer", background="green", fg="white").grid(row=0, column=0)
    tkinter.Label(card_frame, textvariable=dealer_score_label, background="green", fg="white").grid(row=1, column=0)

    # Embedded frame to hold the dealer card images
    dealer_card_frame = tkinter.Frame(card_frame, background="green")
    dealer_card_frame.grid(row=0, column=1, sticky="ew", rowspan=2)

    player_score_label = tkinter.IntVar()

    tkinter.Label(card_frame, text="Player", background="green", fg="white").grid(row=2, column=0)
    tkinter.Label(card_frame, textvariable=player_score_label, background="green", fg="white").grid(row=3, column=0)

    # Embedded frame to hold the player card images
    player_card_frame = tkinter.Frame(card_frame, background="green")
    player_card_frame.grid(row=2, column=1, sticky="ew", rowspan=2)

    button_frame = tkinter.Frame(main_window, background="green")
    button_frame.grid(row=3, column=0, columnspan=3, sticky="ew")

    dealer_button = tkinter.Button(button_frame, text="Stay", command=deal_dealer)
    dealer_button.grid(row=0, column=0, padx=10, pady=10)
    player_button = tkinter.Button(button_frame, text="Hit", command=deal_player)
    player_button.grid(row=0, column=1, padx=10, pady=10)
    reset_button = tkinter.Button(button_frame, text="New Game", command=reset)
    reset_button.grid(row=0, column=2, padx=10, pady=10)

    # Load cards
    cards = []
    load_images(cards)

    # Create a new deck of cards and shuffle
    deck = list(cards)
    random.shuffle(deck)

    # Create the list to store the dealer and player hands
    dealer_hand = []
    player_hand = []
    first_deal()

    main_window.mainloop()


# Globals
deck = None
cards = None
dealer_button = None
player_button = None
dealer_hand = None
player_hand = None
dealer_wins_text = None
player_wins_text = None
result_text = None
main_window = None
player_score_label = None
dealer_score_label = None
player_card_frame = None
dealer_card_frame = None

if __name__ == "__main__":
    play_game()
