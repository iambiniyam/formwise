from formwise.detect import candidates_from_lines


def test_candidates_from_labels():
    lines = [
        ([(10, 10), (80, 10), (80, 40), (10, 40)], "Name:", 0.9),
        ([(10, 60), (90, 60), (90, 90), (10, 90)], "Email:", 0.9),
        ([(10, 110), (120, 110), (120, 140), (10, 140)], "Total amount:", 0.9),
        ([(10, 160), (90, 160), (90, 190), (10, 190)], "Invoice", 0.9),
        ([(10, 210), (90, 210), (90, 240), (10, 240)], "Thank you", 0.9),
    ]
    found = candidates_from_lines(lines, 600, 800)
    assert [item.label for item in found] == ["Name", "Email", "Total Amount", "Invoice"]
    assert all(0 <= item.x <= 1 and 0 <= item.y <= 1 for item in found)
